"use client";

export default function GlobalError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body className="min-h-full bg-slate-950 text-slate-100 antialiased">
        <div className="flex min-h-screen flex-col items-center justify-center gap-3 px-6 text-center">
          <h1 className="text-lg font-semibold">Something went wrong</h1>
          <p className="max-w-md text-sm text-slate-400">
            The application failed to load. Retry, or refresh the page.
          </p>
          <button
            type="button"
            onClick={() => reset()}
            className="rounded-md bg-indigo-500 px-4 py-2 text-sm font-medium text-white"
          >
            Try again
          </button>
        </div>
      </body>
    </html>
  );
}
