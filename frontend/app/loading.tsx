export default function Loading() {
  return (
    <main className="max-w-6xl mx-auto px-6 py-8">
      <div className="h-8 w-48 bg-muted rounded animate-pulse mb-8" />
      <div className="grid grid-cols-3 gap-4 mb-8">
        {[0, 1, 2].map((i) => (
          <div key={i} className="rounded-lg border border-border bg-card p-6 h-24 animate-pulse" />
        ))}
      </div>
      <div className="rounded-lg border border-border overflow-hidden">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-12 border-b border-border bg-card animate-pulse" />
        ))}
      </div>
    </main>
  );
}
