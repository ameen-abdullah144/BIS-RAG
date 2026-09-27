export const meta = {
  name: 'enhance-laboratories-data',
  description: 'Enhance laboratories data for all IS numbers using LIMS',
  phases: [{ title: 'Enhance Laboratories' }]
};

// Load configuration to get IS numbers
const fs = await import('fs');
const path = await import('path');

const configPath = path.join(process.cwd(), 'config', 'niches', 'water_heaters.json');
const configContent = fs.readFileSync(configPath, 'utf8');
const config = JSON.parse(configContent);
const isNumbers = config.is_numbers.map(entry => entry.is_number);

console.log(`Enhancing laboratories data for ${isNumbers.length} IS numbers:`);
isNumbers.forEach(isNum => console.log(`  - ${isNum}`));

// Import the LaboratoriesCollector
const { LaboratoriesCollector } = await import('./collectors/labs.js');

const collector = new LaboratoriesCollector({ storage_base: './storage/data', delay: 1.0 });

// Process each IS number
const results = await pipeline(
  isNumbers,
  async (is_number) => {
    console.log(`\nProcessing ${is_number}...`);

    // Load metadata
    const dirName = is_number
      .split(':')[0]
      .replace(/ /g, '_')
      .replace(/[()]/g, '')
      .replace(/\//g, '_');
    const metadataPath = path.join(process.cwd(), 'storage', 'data', dirName, 'metadata.json');

    let metadata;
    try {
      const metadataContent = fs.readFileSync(metadataPath, 'utf8');
      metadata = JSON.parse(metadataContent);
    } catch (error) {
      console.error(`Failed to load metadata for ${is_number}: ${error}`);
      return null;
    }

    // Collect laboratories data
    try {
      const updatedMetadata = await collector.collect_laboratories(metadata);
      console.log(`  ✓ Found ${updatedMetadata.laboratories?.length || 0} laboratories for ${is_number}`);
      return updatedMetadata;
    } catch (error) {
      console.error(`  ✗ Failed to collect laboratories for ${is_number}: ${error}`);
      return metadata; // Return original on failure
    }
  },
  async (updatedMetadata) => {
    if (!updatedMetadata) return null;

    // Save updated metadata
    const dirName = updatedMetadata.is_number
      .split(':')[0]
      .replace(/ /g, '_')
      .replace(/[()]/g, '')
      .replace(/\//g, '_');
    const metadataPath = path.join(process.cwd(), 'storage', 'data', dirName, 'metadata.json');

    try {
      fs.writeFileSync(metadataPath, JSON.stringify(updatedMetadata, null, 2));
      console.log(`  ✓ Saved updated metadata for ${updatedMetadata.is_number}`);
      return updatedMetadata.is_number;
    } catch (error) {
      console.error(`  ✗ Failed to save metadata for ${updatedMetadata.is_number}: ${error}`);
      return null;
    }
  }
);

// Filter out null results and count successes
const successful = results.filter(r => r !== null);
console.log(`\n✅ Laboratories enhancement complete: ${successful.length}/${isNumbers.length} IS numbers processed successfully`);

// Return summary
const result = {
  processed: successful.length,
  total: isNumbers.length,
  successful_is_numbers: successful
};

// In a workflow, we need to return the result
console.log('Workflow result:', JSON.stringify(result, null, 2));