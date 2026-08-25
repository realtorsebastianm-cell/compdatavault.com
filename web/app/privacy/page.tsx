import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy — CompDataVault",
};

// NOTE: this is a first-pass draft, not attorney-reviewed. Open items
// before publishing: name the actual LLM provider in section 3, fill in
// jurisdiction-specific rights language in section 5 (GDPR/CCPA/etc. as
// applicable to your actual user base), confirm data-residency details
// for section 9, and confirm actual cookie usage for section 10. See the
// delivery notes from the drafting session for the full list.
const SECTIONS: { heading: string; paragraphs: string[] }[] = [
  {
    heading: "1. Information We Collect",
    paragraphs: [
      "Account information: email address, password (stored as a salted bcrypt hash, never in plain text), and any profile information you provide.",
      "User Content: flyers, documents, images, and other files you upload; text queries you submit (e.g., through Ask AI or the Value estimator); saved search criteria; and comp data you enter or edit manually.",
      "Forwarded email content: if you use the email-forwarding upload feature, the content and attachments of emails you send to your CompDataVault ingestion address, and the email addresses of any additional inboxes you authorize to forward on your behalf.",
      "Communications: any messages you send us for support or other purposes.",
      "Usage and log data: pages visited, features used, timestamps, IP address, browser type, and similar technical information collected automatically by our hosting and infrastructure providers.",
      "We do not knowingly collect sensitive personal information (e.g., government ID numbers, financial account credentials, health information) through the Service.",
    ],
  },
  {
    heading: "2. How We Use Information",
    paragraphs: [
      "We use the information described above to provide, operate, and maintain the Service, including extracting structured comp data from uploaded documents; to authenticate your account and enforce data isolation between users; to generate features you request, such as saved-search matching, valuation estimates, geocoding, and mapping; to communicate with you about your account, including saved-search alerts and service notices; to monitor, secure, and improve the Service; and to comply with legal obligations.",
      "We do not sell your personal information or your User Content to third parties.",
    ],
  },
  {
    heading: "3. How We Share Information",
    paragraphs: [
      "Service providers: we use third-party providers to operate the Service, including our hosting and database infrastructure; Cloudflare R2 for uploaded flyer file storage; Cloudflare Email Routing to receive flyers and verification emails you forward to the Service; the U.S. Census Bureau's public geocoding API to convert property addresses into map coordinates (only the address text is sent); OpenStreetMap for map tile rendering; and a third-party large language model provider ([INSERT PROVIDER NAME]) to extract structured data from uploaded documents and to answer natural-language queries. We do not permit these providers to use your data to train their models outside the terms of our agreement with them.",
      "Legal requirements: we may disclose information if required by law, subpoena, or other legal process, or if we believe in good faith that disclosure is necessary to protect our rights, your safety, or the safety of others.",
      "Business transfers: if CompDataVault is involved in a merger, acquisition, or sale of assets, your information may be transferred as part of that transaction, and we will provide notice before it becomes subject to a different privacy policy.",
      "With your direction: we share information when you direct us to, such as using the export feature, or when another user's saved search matches a comp you added (only the comp data itself is exposed via matching, not your account information).",
    ],
  },
  {
    heading: "4. Data Retention",
    paragraphs: [
      "We retain your account information and User Content for as long as your account is active. If you delete a comp, flyer, or your account, we delete the associated data from our active systems within [INSERT TIMEFRAME], except where retention is required for legal, security, or legitimate business purposes such as backups.",
    ],
  },
  {
    heading: "5. Your Rights and Choices",
    paragraphs: [
      "Depending on your location, you may have rights to access the personal information we hold about you, correct inaccurate information, delete your account and associated data, export your data in a portable format, and object to or restrict certain processing.",
      "To exercise these rights, contact us at [INSERT CONTACT EMAIL]. We will respond within the timeframe required by applicable law. [Jurisdiction-specific rights language, e.g. under GDPR/UK GDPR or CCPA/CPRA, to be finalized based on where your users are located.]",
    ],
  },
  {
    heading: "6. Data Security",
    paragraphs: [
      "We use reasonable administrative, technical, and physical safeguards designed to protect your information, including encryption of data in transit, hashed password storage, and access controls limiting data to your own account. No method of transmission or storage is completely secure, and we cannot guarantee absolute security.",
    ],
  },
  {
    heading: "7. Data Isolation Between Users",
    paragraphs: [
      "CompDataVault is a multi-tenant platform. Your comp data, uploaded flyers, saved searches, and account information are logically isolated and are not visible to other users, except where you explicitly authorize a second inbox to forward flyers into your account via the authorized-sender feature, or as otherwise described in this policy.",
    ],
  },
  {
    heading: "8. Children's Privacy",
    paragraphs: [
      "The Service is intended for business use by commercial real estate professionals and is not directed to individuals under 18. We do not knowingly collect information from children. If you believe a child has provided us information, contact us and we will delete it.",
    ],
  },
  {
    heading: "9. International Data Transfers",
    paragraphs: [
      "[Data residency and transfer-mechanism details to be completed based on where our hosting, database, and storage providers physically locate data.]",
    ],
  },
  {
    heading: "10. Cookies and Tracking",
    paragraphs: [
      "[Actual cookie/tracking usage to be confirmed and described here before publishing.]",
    ],
  },
  {
    heading: "11. Changes to This Policy",
    paragraphs: [
      "We may update this Privacy Policy from time to time. Material changes will be communicated before taking effect. The “Last Updated” date at the top of this policy reflects the most recent revision.",
    ],
  },
  {
    heading: "12. Contact Us",
    paragraphs: ["Questions about this Privacy Policy can be directed to [INSERT CONTACT EMAIL]."],
  },
];

export default function PrivacyPage() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="font-serif text-3xl font-bold tracking-tight">
        Privacy Policy
      </h1>
      <p className="mt-2 text-sm text-dim">
        Effective Date: [INSERT DATE] &middot; Last Updated: [INSERT DATE]
      </p>
      <p className="mt-6 border border-line bg-accent/[0.03] px-4 py-3 text-sm text-dim">
        Draft under legal review &mdash; not yet finalized.
      </p>

      <div className="mt-10 space-y-8 text-sm leading-relaxed text-foreground">
        {SECTIONS.map((section) => (
          <section key={section.heading}>
            <h2 className="font-serif text-lg font-semibold">
              {section.heading}
            </h2>
            {section.paragraphs.map((p, i) => (
              <p key={i} className="mt-3 text-dim">
                {p}
              </p>
            ))}
          </section>
        ))}
      </div>
    </div>
  );
}
