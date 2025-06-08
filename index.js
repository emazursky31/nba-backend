require('dotenv').config();
const express = require('express');
const http = require('http');
const cors = require('cors'); // <-- Add this
const { Server } = require('socket.io');
const { Client } = require('pg');

const rooms = {};

const app = express();
const server = http.createServer(app);

// ✅ Add CORS support for both Express and Socket.IO
const FRONTEND_ORIGIN = 'https://nba-teammate-game.vercel.app';

const io = new Server(server, {
  cors: {
    origin: FRONTEND_ORIGIN,
    methods: ['GET', 'POST'],
    credentials: true,
  },
});

app.use(cors({
  origin: FRONTEND_ORIGIN,
  credentials: true,
}));

const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});

const client = new Client({
  connectionString: process.env.SUPABASE_DB_URL,
});

client.connect()
  .then(() => console.log('✅ Connected to Supabase PostgreSQL!'))
  .catch(err => {
    console.error('Connection error:', err);
    process.exit(1);
  });

app.use(express.json());

// Add this to serve your frontend files in /public
app.use(express.static('public'));

app.get('/', (req, res) => {
  res.send('NBA Teammate Game Backend with Socket.IO is running!');
});

app.get('/players', async (req, res) => {
  const input = (req.query.q || '').trim();

  if (!input) {
    return res.json([]);
  }


  const names = input.split(/\s+/);

  // Query to get player plus current team abbreviation (latest stint end_date is max)
  let query;
  let params;

  if (names.length === 1) {
    // Search players where first OR last name starts with input
    // We assume player_name is "First Last" format; we'll use ILIKE with wildcards
    query = `
      SELECT DISTINCT p.player_id, p.player_name,
        (SELECT pts.team_abbr 
         FROM player_team_stints pts 
         WHERE pts.player_id = p.player_id 
         ORDER BY pts.end_date DESC LIMIT 1) AS current_team
      FROM players p
      WHERE 
        p.player_name ILIKE $1 || '%'  -- matches "Kevin" or "LeBron"
        OR p.player_name ILIKE '% ' || $1 || '%'  -- matches last names starting with input
      ORDER BY p.player_name
      LIMIT 20;
    `;
    params = [names[0]];
  } else {
    // If input has two parts, treat as first + last name starts with each
    query = `
      SELECT DISTINCT p.player_id, p.player_name,
        (SELECT pts.team_abbr 
         FROM player_team_stints pts 
         WHERE pts.player_id = p.player_id 
         ORDER BY pts.end_date DESC LIMIT 1) AS current_team
      FROM players p
      WHERE 
        p.player_name ILIKE $1 || '%'  -- first name starts with first input
        AND p.player_name ILIKE '% ' || $2 || '%'  -- last name starts with second input
      ORDER BY p.player_name
      LIMIT 20;
    `;
    params = [names[0], names[1]];
  }

  try {
    const result = await client.query(query, params);
    res.json(result.rows);
  } catch (err) {
    console.error('Error querying players:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});


// In-memory games state: roomId -> game data
const games = {}; // Assuming this is your existing game tracking



io.on('connection', (socket) => {
  console.log(`User connected: ${socket.id}`);

// Player joins a game room
socket.on('joinGame', ({ roomId, username }) => {
  socket.join(roomId);
  console.log(`User ${username} (${socket.id}) joined room ${roomId}`);

  // Initialize game if room doesn't exist
  if (!games[roomId]) {
    games[roomId] = {
      players: [],
      usernames: {},
      currentTurn: 0,
      currentPlayerName: null,
      timer: null,
      timeLeft: 15,
      teammates: [],
      successfulGuesses: [],
      rematchVotes: new Set(),
    };
  }

  const game = games[roomId];

  if (!game.players.includes(socket.id)) {
    game.players.push(socket.id);
    game.usernames[socket.id] = username;
  }

  io.to(roomId).emit('playersUpdate', game.players.length);

  // ✅ START GAME when 2 players are in
  if (game.players.length === 2) {
    startGame(roomId);
  }
});


  // Handle player guess
  socket.on('playerGuess', async ({ roomId, guess }) => {
    const game = games[roomId];
    if (!game) return;

    const normalizedGuess = guess.trim().toLowerCase();

    // 🚫 Game hasn't started yet
    if (!game.leadoffPlayer) {
      socket.emit('message', "Game hasn't started properly yet.");
      return;
    }

    // 🚫 Reject guessing leadoff player
    if (normalizedGuess === game.leadoffPlayer.toLowerCase()) {
      socket.emit('message', `You can't guess the starting player: "${game.leadoffPlayer}"`);
      return;
    }

    // 🚫 Already guessed
    const alreadyGuessed = game.successfulGuesses.some(name => name.toLowerCase() === normalizedGuess);
    if (alreadyGuessed) {
      socket.emit('message', `"${guess}" has already been guessed.`);
      return;
    }

    // ✅ Valid teammate
    const validGuess = game.teammates.some(t => t.toLowerCase() === normalizedGuess);

    if (validGuess) {
      clearInterval(game.timer);

      game.successfulGuesses.push(guess);
      game.currentTurn = (game.currentTurn + 1) % 2;
      game.currentPlayerName = guess;
      game.teammates = await getTeammates(game.currentPlayerName);
      game.timeLeft = 15;

      io.to(roomId).emit('turnEnded', {
        successfulGuess: `Player ${socket.id} guessed "${guess}" successfully!`,
        nextPlayerId: game.players[game.currentTurn],
        currentPlayerName: game.currentPlayerName,
        timeLeft: game.timeLeft,
      });

      startTurnTimer(roomId);
    } else {
      socket.emit('message', `Incorrect guess: "${guess}"`);
    }
  });

socket.on('requestRematch', ({ roomId }) => {
  const game = games[roomId];
  if (!game) return;

  const username = game.usernames[socket.id];
  if (!username) return;

  if (!game.rematchVotes) {
  game.rematchVotes = new Set();
}

game.rematchVotes.add(username);


  // Inform the other player(s)
  socket.to(roomId).emit('rematchRequested', { username });

  const playersInRoom = Object.values(game.usernames);
  console.log('Players in room:', playersInRoom);

const allAgreed = playersInRoom.every(name => game.rematchVotes.has(name));

  if (allAgreed) {
    console.log('All players agreed for rematch in room', roomId);

    startGame(roomId);
  }
});







// Disconnect cleanup
socket.on('disconnect', () => {
  console.log(`User disconnected: ${socket.id}`);

  for (const [roomId, game] of Object.entries(games)) {
    const idx = game.players.indexOf(socket.id);
    if (idx !== -1) {
      const disconnectedUsername = game.usernames[socket.id];

      // Remove player from game state
      game.players.splice(idx, 1);
      delete game.usernames[socket.id];
      io.to(roomId).emit('playersUpdate', game.players.length);

      // Clear any timers
      if (game.timer) {
        clearInterval(game.timer);
      }

      // 🧼 Clean up rematchRequests Set properly
      if (game.rematchVotes) {
  game.rematchVotes.delete(disconnectedUsername);

  // Optional: reset if empty
  if (game.rematchVotes.size === 0) {
    game.rematchVotes = new Set();
  }
}


      // End game if not enough players
      if (game.players.length < 2) {
        io.to(roomId).emit('gameOver', 'Not enough players. Game ended.');
        delete games[roomId];
      }

      break; // Player found and removed; no need to check other rooms
    }
  }

    // If you have a separate players object, clean up here:
  // delete players[socket.id];
});




// Helper: get teammates of a player by player_name
async function getTeammates(playerName) {
  const query = `
    WITH player_stints AS (
      SELECT team_abbr, start_date, end_date
      FROM player_team_stints pts
      JOIN players p ON pts.player_id = p.player_id
      WHERE p.player_name = $1
    )
    SELECT DISTINCT p2.player_name
    FROM player_team_stints pts2
    JOIN players p2 ON pts2.player_id = p2.player_id
    JOIN player_stints ps ON pts2.team_abbr = ps.team_abbr
    WHERE p2.player_name != $1
      AND pts2.start_date <= ps.end_date
      AND pts2.end_date >= ps.start_date;
  `;

  try {
    const res = await client.query(query, [playerName]);
    return res.rows.map(r => r.player_name);
  } catch (err) {
    console.error('Error fetching teammates:', err);
    return [];
  }
}


// Starts the game in a room: picks random first player & teammates
async function startGame(roomId) {
  const game = games[roomId];
  if (!game) {
    console.log('❌ No game object found');
    return;
  }

  game.rematchVotes = new Set();  // Reset rematch state
  if (game.timer) clearInterval(game.timer);
  game.successfulGuesses = [];
  game.timeLeft = 15;

  const startIndex = Math.floor(Math.random() * game.players.length);
  game.currentTurn = startIndex;

  // STEP 1: Pick a valid starting player
  game.currentPlayerName = await getRandomPlayer(); // You will update this function
  game.leadoffPlayer = game.currentPlayerName;
  game.teammates = await getTeammates(game.currentPlayerName);

  // STEP 2: Check if teammates exist
  if (!game.teammates || game.teammates.length === 0) {
    io.to(roomId).emit('gameOver', {
      message: `No teammates found for ${game.currentPlayerName}. Game cannot proceed.`,
    });
    delete games[roomId];
    return;
  }

  // Log for debugging
  console.log(`[STARTGAME] room ${roomId} starting with:`);
  console.log(`→ currentPlayerName: ${game.currentPlayerName}`);
  console.log(`→ teammates: ${game.teammates}`);
  console.log(`→ players: ${game.players}`);
  console.log(`→ currentTurn: ${game.currentTurn}`);

  // STEP 3: Emit and start game
  io.to(roomId).emit('gameStarted', {
    firstPlayerId: game.players[startIndex],
    currentPlayerName: game.currentPlayerName,
    timeLeft: game.timeLeft,
  });

  startTurnTimer(roomId);
}


async function getRandomPlayer() {
  const query = `
    WITH player_seasons AS (
      SELECT
        player_id,
        generate_series(CAST(start_season AS INT), CAST(end_season AS INT)) AS season
      FROM player_team_stints
      WHERE start_season >= '2000'
    )
    SELECT p.player_name
    FROM players p
    JOIN (
      SELECT player_id
      FROM player_seasons
      GROUP BY player_id
      HAVING COUNT(DISTINCT season) >= 10
    ) ps ON p.player_id = ps.player_id
    ORDER BY RANDOM()
    LIMIT 1;
  `;

  const res = await client.query(query);
  return res.rows[0]?.player_name || null;
}





// Starts the 15-second countdown timer for a turn
function startTurnTimer(roomId) {
  const game = games[roomId];
  if (!game) return;

  if (game.timer) clearInterval(game.timer);

  game.timer = setInterval(() => {
    game.timeLeft -= 1;

    if (game.timeLeft <= 0) {
      clearInterval(game.timer);

      const loserSocketId = game.players[game.currentTurn];
const winnerSocketId = game.players.find((id) => id !== loserSocketId);

const loserName = game.usernames[loserSocketId];
const winnerName = game.usernames[winnerSocketId];

io.to(roomId).emit('gameOver', {
  message: `Time's up! ${loserName} failed to guess a teammate. ${winnerName} wins!`,
});


      

      // Optionally delete game state here
      delete games[roomId];
      return;
    }

    // Emit remaining time each second
    io.to(roomId).emit('timerTick', { timeLeft: game.timeLeft });
  }, 1000);
}

});

