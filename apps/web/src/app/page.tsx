export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold tracking-tight">
          Oratoria Avaliador
        </h1>
        <p className="text-lg text-gray-600">
          IA que avalia oratoria em video
        </p>
        <div className="inline-flex items-center gap-2 rounded-full bg-green-100 px-4 py-2 text-sm font-medium text-green-800">
          <span className="h-2 w-2 rounded-full bg-green-500" />
          Running
        </div>
      </div>
    </main>
  );
}
