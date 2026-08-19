/**
 * CompDataVault — inbound flyer email Worker
 *
 * Cloudflare Email Routing has one exact-match rule for deals@compdatavault.com
 * pointing at this Worker (sebastian@ keeps its own separate forward-to-Gmail
 * rule; nothing else reaches this Worker, since there's no catch-all). Every
 * broker forwards flyers to that same single address — there's no per-broker
 * routing scheme on the recipient side at all. The backend figures out whose
 * vault a flyer belongs to by matching the sender's From address against its
 * User.email column, not by anything in the To address.
 *
 * The Worker does the minimum possible processing itself: grab the raw MIME
 * email, hand it off to the FastAPI backend as multipart/form-data, and reply
 * to the sender with a plain-language summary of what happened. All the real
 * work (MIME parsing, attachment extraction, Anthropic extraction, DB writes,
 * sender matching) stays in the backend where it's easy to test, log, and
 * redeploy without touching DNS/edge config. Keeping the Worker this thin also
 * keeps it well inside the free-tier CPU limits no matter how much volume
 * comes in.
 */

import { EmailMessage } from "cloudflare:email";
import { createMimeMessage } from "mimetext";

export default {
	async email(message, env, ctx) {
		const to = (message.to || "").toLowerCase();

		// Belt-and-suspenders: Cloudflare's routing rule should only ever invoke
		// this Worker for the one address it's bound to, but check anyway in
		// case the rule is ever changed to a catch-all by mistake.
		if (to !== (env.INBOUND_ADDRESS || "").toLowerCase()) {
			message.setReject("Address not accepted");
			return;
		}

		// Cloudflare already enforces a 25 MiB inbound message cap, but double-check
		// before we buffer the whole thing into memory / ship it onward.
		if (message.rawSize && message.rawSize > 25 * 1024 * 1024) {
			message.setReject("Message too large");
			return;
		}

		let rawBuffer;
		try {
			rawBuffer = await new Response(message.raw).arrayBuffer();
		} catch (err) {
			console.error("Failed to read raw email stream:", err);
			// Transient — ask the sender's server to retry.
			message.setReject("Temporary error reading message, please resend");
			return;
		}

		const formData = new FormData();
		formData.append("from_address", message.from || "");
		formData.append("to_address", message.to || "");
		formData.append("subject", message.headers.get("subject") || "");
		formData.append(
			"raw_email",
			new Blob([rawBuffer], { type: "message/rfc822" }),
			"email.eml"
		);

		let response;
		try {
			response = await fetch(`${env.BACKEND_URL}/ingest/email`, {
				method: "POST",
				headers: {
					"X-Ingest-Secret": env.INGEST_SHARED_SECRET,
				},
				body: formData,
			});
		} catch (err) {
			console.error("Could not reach backend:", err);
			message.setReject("Temporary processing error, please resend");
			return;
		}

		if (response.ok) {
			const results = await response.json().catch(() => null);
			if (results && results.length) {
				await replySafely(message, env, buildSuccessBody(results, env));
			}
			return;
		}

		const bodyText = await response.text().catch(() => "");
		console.error(`Backend rejected email: ${response.status} ${bodyText}`);

		// 5xx from our own backend = transient, worth a retry from the sender's side.
		if (response.status >= 500) {
			message.setReject("Temporary processing error, please resend");
			return;
		}

		// 400 (no attachment, bad recipient) and 404 (sender doesn't match an
		// account) are things the sender can actually act on, so tell them what
		// happened. 401 (bad shared secret -- an infra misconfiguration, not
		// anything a sender did) and 403 (failed SPF/DKIM -- possible spoofing)
		// stay silent: neither is something to explain to whoever sent this,
		// and confirming a spoof attempt back to its sender is just free
		// reconnaissance for them.
		if (response.status === 400 || response.status === 404) {
			let detail = "";
			try {
				detail = JSON.parse(bodyText).detail || "";
			} catch {
				// bodyText wasn't JSON -- fall back to a generic message below.
			}
			await replySafely(message, env, buildFailureBody(detail));
		}
	},
};

async function replySafely(message, env, textBody) {
	try {
		const subject = message.headers.get("subject") || "";
		const messageId = message.headers.get("Message-ID");

		const reply = createMimeMessage();
		if (messageId) {
			reply.setHeader("In-Reply-To", messageId);
			reply.setHeader("References", messageId);
		}
		reply.setSender(message.to);
		reply.setRecipient(message.from);
		reply.setSubject(subject ? `Re: ${subject}` : "Your flyer");
		reply.addMessage({ contentType: "text/plain", data: textBody });

		await message.reply(new EmailMessage(message.to, message.from, reply.asRaw()));
	} catch (err) {
		// message.reply() throws if the incoming email doesn't have a valid
		// DMARC result, among other things -- not every sender's mail setup
		// will satisfy that. The flyer itself is already ingested by this
		// point regardless of whether the confirmation goes out, so a failed
		// reply is a logged miss, not a failed ingestion.
		console.error("Could not send confirmation reply:", err);
	}
}

function buildSuccessBody(results, env) {
	const frontendUrl = (env.FRONTEND_URL || "https://compdatavault.com").replace(/\/$/, "");
	const lines = [];

	const parsed = results.filter((r) => r.status === "parsed");
	const needsReview = results.filter((r) => r.status === "needs_review");
	const failed = results.filter((r) => r.status === "failed");

	if (results.length === 1) {
		lines.push(summarizeOne(results[0], frontendUrl));
	} else {
		lines.push(`Got ${results.length} attachments from that email:`);
		lines.push("");
		for (const r of results) {
			lines.push(`- ${summarizeOne(r, frontendUrl)}`);
		}
	}

	lines.push("");
	if (needsReview.length) {
		lines.push(
			`${needsReview.length} comp${needsReview.length > 1 ? "s" : ""} could use a second look for low-confidence fields before you rely on ${needsReview.length > 1 ? "them" : "it"}.`
		);
	}
	if (failed.length) {
		lines.push(
			`${failed.length} attachment${failed.length > 1 ? "s" : ""} couldn't be parsed automatically -- you can upload ${failed.length > 1 ? "them" : "it"} manually at ${frontendUrl}/upload if needed.`
		);
	}

	return lines.join("\n");
}

function summarizeOne(result, frontendUrl) {
	if (result.status === "failed") {
		return `Couldn't parse this one${result.error ? `: ${result.error}` : "."}`;
	}
	const dealTypeLabel = result.deal_type === "sale" ? "Sale" : "Lease";
	const link = result.comp_id
		? `${frontendUrl}/comps?type=${result.deal_type}&id=${result.comp_id}`
		: null;
	const reviewNote = result.status === "needs_review" ? " (a few fields need review)" : "";
	return `${dealTypeLabel} comp added to your vault${reviewNote}.${link ? ` ${link}` : ""}`;
}

function buildFailureBody(detail) {
	const lines = ["That email didn't make it into your vault."];
	if (detail) {
		lines.push("");
		lines.push(detail);
	}
	lines.push("");
	lines.push(
		"If you're forwarding from a different email than the one you signed up with, forward from your account email instead, or reply to this thread with any questions."
	);
	return lines.join("\n");
}
