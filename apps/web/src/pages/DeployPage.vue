<template>
  <div class="space-y-4">
    <div>
      <h1 class="text-2xl font-semibold">Deploy</h1>
      <p class="text-sm text-slate-600">
        Deployment automation is planned for upcoming versions.
      </p>
    </div>

    <div class="card p-4 space-y-2 text-sm">
      <div class="font-medium">Planned in v0.1.2+</div>
      <ul class="list-disc pl-5 space-y-1 text-slate-700">
        <li>Analyze <span class="font-mono">package.xml</span> and detect risky metadata</li>
        <li>Prepare a deployment plan (retrieve/merge/deploy steps)</li>
        <li>Support monolithic merge (Custom Labels, Translations)</li>
        <li>Integrate permission trimming (“pruning”)</li>
      </ul>
    </div>
  </div>
</template>
