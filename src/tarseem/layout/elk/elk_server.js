// Long-lived elkjs layout server (ADR-002). Owned by the layout adapter.
// Protocol: newline-delimited JSON. Request {"id","graph":<ELK JSON>} on stdin ->
// Response {"id","ok":true,"graph":<laid-out>} | {"id","ok":false,"error"} on stdout.
// The pinned bundle path is passed as argv[2] so resolution never depends on
// node_modules layout. Requests are serialized; diagnostics go to stderr only,
// keeping stdout a clean one-response-per-line JSON stream.
'use strict';

const bundlePath = process.argv[2];
if (!bundlePath) {
  process.stderr.write('elk-server: missing bundle path argument\n');
  process.exit(1);
}
const ELK = require(bundlePath);
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
    elk
      .layout(req.graph)
      .then((g) => respond({ id, ok: true, graph: g }))
      .catch((e) => respond({ id, ok: false, error: String((e && e.message) || e) }))
  );
}

process.stderr.write('elk-server ready\n');
