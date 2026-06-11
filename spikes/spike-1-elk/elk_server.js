// Long-lived elkjs layout server (Phase-0 spike 1, throwaway).
// Protocol: newline-delimited JSON. Request {"id", "graph": <ELK JSON>} on stdin.
// Response {"id","ok":true,"graph":<laid-out>} or {"id","ok":false,"error"} on stdout.
// Requests are serialized so layout calls never overlap. Diagnostics -> stderr only,
// keeping stdout a clean one-response-per-line JSON stream.
const ELK = require('elkjs/lib/elk.bundled.js');
const elk = new ELK();

let buf = '';
let chain = Promise.resolve();

process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => {
  buf += chunk;
  let nl;
  while ((nl = buf.indexOf('\n')) >= 0) {
    const line = buf.slice(0, nl).trim();
    buf = buf.slice(nl + 1);
    if (line) enqueue(line);
  }
});
process.stdin.on('end', () => process.exit(0));

function respond(obj) {
  process.stdout.write(JSON.stringify(obj) + '\n');
}

function enqueue(line) {
  let req;
  try {
    req = JSON.parse(line);
  } catch (e) {
    respond({ id: null, ok: false, error: 'bad json: ' + e.message });
    return;
  }
  const id = req.id;
  chain = chain.then(() =>
    elk.layout(req.graph)
      .then((g) => respond({ id, ok: true, graph: g }))
      .catch((e) => respond({ id, ok: false, error: String((e && e.message) || e) }))
  );
}

process.stderr.write('elk-server ready\n');
