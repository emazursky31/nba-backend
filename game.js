// game.js
const { Client } = require('pg');

const client = new Client({ connectionString: process.env.SUPABASE_DB_URL });
client.connect();

const gameState = {
  currentPlayer: null,
  lastPlayer: null,
  history: [],
};

async function getTeammates(playerName) {
  const query = `
    SELECT DISTINCT p2.player_name
    FROM player_team_stints pts1
    JOIN player_team_stints pts2
      ON pts1.team_abbr = pts2.team_abbr
      AND pts1.season = pts2.season
    JOIN players p1 ON pts1.player_id = p1.player_id
    JOIN players p2 ON pts2.player_id = p2.player_id
    WHERE p1.player_name = $1 AND p2.player_name != $1
  `;
  const res = await client.query(query, [playerName]);
  return res.rows.map(row => row.player_name);
}

async function isValidMove(prevPlayer, newPlayer) {
  const teammates = await getTeammates(prevPlayer);
  return teammates.includes(newPlayer);
}

module.exports = { gameState, isValidMove };
