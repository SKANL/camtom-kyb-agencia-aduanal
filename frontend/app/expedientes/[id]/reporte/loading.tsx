export default function ReporteLoading() {
  return (
    <main className="max-w-3xl mx-auto px-6 py-8 animate-pulse">
      {/* Breadcrumb skeleton */}
      <div className="mb-6">
        <div className="h-4 w-40 bg-muted rounded" />
        <div className="h-8 w-48 bg-muted rounded mt-2" />
      </div>

      {/* Score hero skeleton */}
      <div className="rounded-xl border border-border bg-card p-6 mb-6">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-2">
            <div className="h-3 w-16 bg-muted rounded" />
            <div className="h-8 w-32 bg-muted rounded" />
            <div className="h-4 w-56 bg-muted rounded" />
          </div>
          <div className="text-right space-y-2">
            <div className="h-3 w-24 bg-muted rounded ml-auto" />
            <div className="h-14 w-20 bg-muted rounded ml-auto" />
          </div>
        </div>
      </div>

      {/* Factors skeleton */}
      <div className="rounded-xl border border-border bg-card p-6 mb-6">
        <div className="h-3 w-48 bg-muted rounded mb-4" />
        {[...Array(4)].map((_, i) => (
          <div key={i} className="flex items-center gap-3 py-2">
            <div className="flex-1 h-4 bg-muted rounded" />
            <div className="w-32 h-1.5 bg-muted rounded-full" />
            <div className="w-14 h-4 bg-muted rounded" />
          </div>
        ))}
      </div>

      {/* Actions skeleton */}
      <div className="flex gap-3">
        <div className="h-10 w-32 bg-muted rounded-lg" />
        <div className="h-10 w-36 bg-muted rounded-lg" />
      </div>
    </main>
  );
}
