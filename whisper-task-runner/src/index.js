const server = require('./server');
const worker = require('./worker');

console.log('🚀 Starting Whisper Task Runner...');

// Start API server
server.start();

// Start worker
worker.start();

