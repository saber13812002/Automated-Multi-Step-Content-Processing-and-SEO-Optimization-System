const express = require('express');
const cors = require('cors');
const db = require('./db');
const fileQueue = require('./fileQueue');
const config = require('./config');

const app = express();

app.use(cors());
app.use(express.json());

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', machineId: config.machineId });
});

// Get next tasks
app.post('/api/tasks/claim', async (req, res) => {
  try {
    const limit = parseInt(req.body.limit || req.query.limit || '10', 10);
    const tasks = await db.getPendingTasks(limit);
    res.json({ tasks });
  } catch (error) {
    console.error('Error claiming tasks:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get task by ID
app.get('/api/tasks/:id', async (req, res) => {
  try {
    const taskId = parseInt(req.params.id, 10);
    const task = await db.getTaskById(taskId);
    
    if (!task) {
      return res.status(404).json({ error: 'Task not found' });
    }
    
    res.json({ task });
  } catch (error) {
    console.error('Error getting task:', error);
    res.status(500).json({ error: error.message });
  }
});

// Get all tasks with filters
app.get('/api/tasks', async (req, res) => {
  try {
    const filters = {
      status: req.query.status,
      assignedTo: req.query.assigned_to,
    };
    const limit = parseInt(req.query.limit || '100', 10);
    const offset = parseInt(req.query.offset || '0', 10);
    
    const tasks = await db.getAllTasks(filters, limit, offset);
    res.json({ tasks });
  } catch (error) {
    console.error('Error getting tasks:', error);
    res.status(500).json({ error: error.message });
  }
});

// Create a new task
app.post('/api/tasks', async (req, res) => {
  try {
    const { inputPath, outputPath } = req.body;
    
    if (!inputPath) {
      return res.status(400).json({ error: 'inputPath is required' });
    }
    
    const taskId = await db.createTask(inputPath, outputPath);
    res.status(201).json({ taskId, message: 'Task created successfully' });
  } catch (error) {
    console.error('Error creating task:', error);
    res.status(500).json({ error: error.message });
  }
});

// Bulk create tasks
app.post('/api/tasks/bulk', async (req, res) => {
  try {
    const { tasks } = req.body;
    
    if (!Array.isArray(tasks) || tasks.length === 0) {
      return res.status(400).json({ error: 'tasks array is required' });
    }
    
    const taskIds = await db.bulkCreateTasks(tasks);
    res.status(201).json({ taskIds, count: taskIds.length });
  } catch (error) {
    console.error('Error bulk creating tasks:', error);
    res.status(500).json({ error: error.message });
  }
});

// Mark task as picked
app.post('/api/tasks/:id/picked', async (req, res) => {
  try {
    const taskId = parseInt(req.params.id, 10);
    const task = await db.getTaskById(taskId);
    
    if (!task) {
      return res.status(404).json({ error: 'Task not found' });
    }
    
    // This is handled in getPendingTasks, but we can add explicit endpoint
    res.json({ message: 'Task picked', taskId });
  } catch (error) {
    console.error('Error marking task as picked:', error);
    res.status(500).json({ error: error.message });
  }
});

// Complete a task
app.post('/api/tasks/:id/complete', async (req, res) => {
  try {
    const taskId = parseInt(req.params.id, 10);
    const { outputPath } = req.body;
    
    if (!outputPath) {
      return res.status(400).json({ error: 'outputPath is required' });
    }
    
    await db.completeTask(taskId, outputPath);
    res.json({ message: 'Task completed', taskId });
  } catch (error) {
    console.error('Error completing task:', error);
    res.status(500).json({ error: error.message });
  }
});

// Fail a task
app.post('/api/tasks/:id/fail', async (req, res) => {
  try {
    const taskId = parseInt(req.params.id, 10);
    const { errorMessage } = req.body;
    
    await db.failTask(taskId, errorMessage || 'Unknown error');
    res.json({ message: 'Task marked as failed', taskId });
  } catch (error) {
    console.error('Error failing task:', error);
    res.status(500).json({ error: error.message });
  }
});

// Scan input directory
app.get('/api/files/scan', async (req, res) => {
  try {
    const files = await fileQueue.scanInputDirectory();
    res.json({ files, count: files.length });
  } catch (error) {
    console.error('Error scanning directory:', error);
    res.status(500).json({ error: error.message });
  }
});

function start() {
  db.initPool();
  
  app.listen(config.apiPort, '0.0.0.0', () => {
    console.log(`🚀 API server listening on port ${config.apiPort}`);
    console.log(`📁 Input directory: ${config.inputDir}`);
    console.log(`📁 Output directory: ${config.outputDir}`);
    console.log(`⏰ Active window: ${config.activeStartHour}:00 - ${config.activeEndHour}:00`);
  });
}

module.exports = { start, app };

