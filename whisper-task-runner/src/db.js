const mysql = require('mysql2/promise');
const config = require('./config');

let pool = null;

/**
 * Initialize MySQL connection pool
 */
function initPool() {
  if (!pool) {
    pool = mysql.createPool({
      host: config.mysql.host,
      port: config.mysql.port,
      user: config.mysql.user,
      password: config.mysql.password,
      database: config.mysql.database,
      waitForConnections: true,
      connectionLimit: 10,
      queueLimit: 0,
      enableKeepAlive: true,
      keepAliveInitialDelay: 0,
    });
  }
  return pool;
}

/**
 * Get pending tasks from database
 * @param {number} limit - Maximum number of tasks to retrieve
 * @returns {Promise<Array>} - Array of task objects
 */
async function getPendingTasks(limit = 10) {
  const connection = await initPool().getConnection();
  try {
    await connection.beginTransaction();
    
    // Get tasks that are pending or timed out
    const timeoutDate = new Date();
    timeoutDate.setMinutes(timeoutDate.getMinutes() - config.taskTimeoutMinutes);
    
    const [rows] = await connection.execute(
      `SELECT id, input_path, output_path, status, assigned_to, picked_at 
       FROM tasks 
       WHERE (status = 'pending' AND (picked_at IS NULL OR picked_at < ?))
          OR (status = 'processing' AND picked_at < ?)
       ORDER BY created_at ASC
       LIMIT ?`,
      [timeoutDate, timeoutDate, limit]
    );
    
    // Update selected tasks to processing
    if (rows.length > 0) {
      const taskIds = rows.map(r => r.id);
      await connection.execute(
        `UPDATE tasks 
         SET status = 'processing', 
             picked_at = NOW(), 
             assigned_to = ?
         WHERE id IN (${taskIds.map(() => '?').join(',')})`,
        [config.machineId, ...taskIds]
      );
    }
    
    await connection.commit();
    return rows;
  } catch (error) {
    await connection.rollback();
    throw error;
  } finally {
    connection.release();
  }
}

/**
 * Mark task as completed
 * @param {number} taskId - Task ID
 * @param {string} outputPath - Path to output SRT file
 */
async function completeTask(taskId, outputPath) {
  const connection = await initPool().getConnection();
  try {
    await connection.execute(
      `UPDATE tasks 
       SET status = 'done', 
           output_path = ?, 
           finished_at = NOW() 
       WHERE id = ?`,
      [outputPath, taskId]
    );
  } finally {
    connection.release();
  }
}

/**
 * Mark task as failed
 * @param {number} taskId - Task ID
 * @param {string} errorMessage - Error message
 */
async function failTask(taskId, errorMessage) {
  const connection = await initPool().getConnection();
  try {
    await connection.execute(
      `UPDATE tasks 
       SET status = 'failed', 
           error_message = ?, 
           finished_at = NOW() 
       WHERE id = ?`,
      [errorMessage, taskId]
    );
  } finally {
    connection.release();
  }
}

/**
 * Create a new task
 * @param {string} inputPath - Path to input video file
 * @param {string} outputPath - Path to output SRT file (optional)
 * @returns {Promise<number>} - Task ID
 */
async function createTask(inputPath, outputPath = null) {
  const connection = await initPool().getConnection();
  try {
    const [result] = await connection.execute(
      `INSERT INTO tasks (input_path, output_path, status) 
       VALUES (?, ?, 'pending')`,
      [inputPath, outputPath]
    );
    return result.insertId;
  } finally {
    connection.release();
  }
}

/**
 * Bulk create tasks
 * @param {Array<{inputPath: string, outputPath?: string}>} tasks - Array of task objects
 * @returns {Promise<Array<number>>} - Array of task IDs
 */
async function bulkCreateTasks(tasks) {
  const connection = await initPool().getConnection();
  try {
    await connection.beginTransaction();
    
    const taskIds = [];
    for (const task of tasks) {
      const [result] = await connection.execute(
        `INSERT INTO tasks (input_path, output_path, status) 
         VALUES (?, ?, 'pending')`,
        [task.inputPath, task.outputPath || null]
      );
      taskIds.push(result.insertId);
    }
    
    await connection.commit();
    return taskIds;
  } catch (error) {
    await connection.rollback();
    throw error;
  } finally {
    connection.release();
  }
}

/**
 * Get task by ID
 * @param {number} taskId - Task ID
 * @returns {Promise<Object|null>} - Task object or null
 */
async function getTaskById(taskId) {
  const connection = await initPool().getConnection();
  try {
    const [rows] = await connection.execute(
      'SELECT * FROM tasks WHERE id = ?',
      [taskId]
    );
    return rows.length > 0 ? rows[0] : null;
  } finally {
    connection.release();
  }
}

/**
 * Get all tasks with optional filters
 * @param {Object} filters - Filter options (status, assigned_to, etc.)
 * @param {number} limit - Maximum number of tasks
 * @param {number} offset - Offset for pagination
 * @returns {Promise<Array>} - Array of task objects
 */
async function getAllTasks(filters = {}, limit = 100, offset = 0) {
  const connection = await initPool().getConnection();
  try {
    let query = 'SELECT * FROM tasks WHERE 1=1';
    const params = [];
    
    if (filters.status) {
      query += ' AND status = ?';
      params.push(filters.status);
    }
    
    if (filters.assignedTo) {
      query += ' AND assigned_to = ?';
      params.push(filters.assignedTo);
    }
    
    query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?';
    params.push(limit, offset);
    
    const [rows] = await connection.execute(query, params);
    return rows;
  } finally {
    connection.release();
  }
}

module.exports = {
  initPool,
  getPendingTasks,
  completeTask,
  failTask,
  createTask,
  bulkCreateTasks,
  getTaskById,
  getAllTasks,
};

