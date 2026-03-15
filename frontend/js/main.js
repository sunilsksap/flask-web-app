const { app, BrowserWindow, ipcMain } = require('electron');
const Database = require('better-sqlite3');
const entDb = new Database('enterprise.db');

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    webPreferences: { preload: __dirname + '/preload.js' }
  });
  mainWindow.loadFile('login.html');
}

ipcMain.on('login-attempt', (event, data) => {
  const user = entDb.prepare('SELECT * FROM users WHERE username = ? AND password = ?').get(data.u, data.p);
  mainWindow.webContents.send('login-result', !!user);
});

app.whenReady().then(createWindow);