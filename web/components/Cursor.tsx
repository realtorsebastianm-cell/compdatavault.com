export default function Cursor({ className = "" }: { className?: string }) {
  return <span className={`cursor-blink ${className}`} aria-hidden="true" />;
}
