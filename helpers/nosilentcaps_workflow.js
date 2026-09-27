export const meta = {
  name: 'nosilentcaps-demo',
  description: 'Demonstrate the No silent caps quality pattern',
  phases: [
    { title: 'Discover', detail: 'Find all test files' },
    { title: 'Process', detail: 'Process files with limit and log what was dropped' },
  ],
}

// Helper function to simulate file processing
async function processFile(filePath) {
  // In a real workflow, this would do actual analysis
  // For demo, we'll just return a simple result
  return {
    file: filePath,
    lines: Math.floor(Math.random() * 100) + 50,
    status: 'processed'
  }
}

// Main workflow
phase('Discover')
const allTestFiles = await agent('Find all test files in the project', {
  schema: {
    type: 'object',
    properties: {
      files: {
        type: 'array',
        items: { type: 'string' }
      }
    },
    required: ['files']
  }
})

// Filter to get actual file paths if needed
const testFiles = allTestFiles && allTestFiles.files ?
  allTestFiles.files.filter(f => f.endsWith('.py' && f.includes('test'))) :
  []

log(`Discovered ${testFiles.length} test files`)

phase('Process')
// Set a processing limit to demonstrate bounding
const PROCESS_LIMIT = 5
const filesToProcess = testFiles.slice(0, PROCESS_LIMIT)
const filesDropped = testFiles.length > PROCESS_LIMIT ?
  testFiles.slice(PROCESS_LIMIT) :
  []

// Process the limited set
const results = await parallel(
  filesToProcess.map(file => () =>
    agent(`Process ${file}`, {
      schema: {
        type: 'object',
        properties: {
          file: { type: 'string' },
          lines: { type: 'integer' },
          status: { type: 'string' }
        },
        required: ['file', 'lines', 'status']
      }
    })
  )
)

// Filter out null results (from agent errors/skips)
const validResults = results.filter(Boolean)

// LOG WHAT WAS DROPPED - This is the "No silent caps" principle in action
if (filesDropped.length > 0) {
  log(`Processed ${validResults.length} files, dropped ${filesDropped.length} files due to processing limit`)
  // In a real workflow, you might also log which specific files were dropped
  // log(`Dropped files: ${filesDropped.join(', ')}`)
} else {
  log(`Processed all ${validResults.length} test files`)
}

return {
  processedCount: validResults.length,
  droppedCount: filesDropped.length,
  totalDiscovered: testFiles.length,
  results: validResults
}