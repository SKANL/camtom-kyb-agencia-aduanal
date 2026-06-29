export default function Loading() {
  return (
    <main className="max-w-5xl mx-auto px-6 py-8">
      <div className="h-6 w-32 bg-muted rounded animate-pulse mb-2" />
      <div className="h-8 w-64 bg-muted rounded animate-pulse mb-1" />
      <div className="h-4 w-32 bg-muted rounded animate-pulse mb-8" />
      <div className="grid grid-cols-7 gap-3 mb-8">
        {Array.from({ length: 7 }).map((_, i) => (
          <div key={i} className="h-28 rounded-xl bg-card animate-pulse" />
        ))}
      </div>
    </main>
  );
}
