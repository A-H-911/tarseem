// Long-lived libavoid-js (WASM) routing server (ADR-006). Owned by the LibavoidRouter
// adapter; OPTIONAL + experimental (LGPL-2.1, off by default). Protocol mirrors the elk
// server: newline-delimited JSON. Request {"id","route":{nodes,edges,options}} on stdin ->
// Response {"id","ok":true,"edges":[{id,points}]} | {"id","ok":false,"error"} on stdout.
// argv[2] = path to the vendored index-node.mjs glue; argv[3] = path to libavoid.wasm.
// libavoid's object model never leaves this process; the adapter only sees routed points.
'use strict';

const gluePath = process.argv[2];
const wasmPath = process.argv[3];
if (!gluePath || !wasmPath) {
  process.stderr.write('libavoid-server: missing glue or wasm path argument\n');
  process.exit(1);
}

const CONN_PIN_CENTRE = 1; // our class id for the per-shape centre connection pin
const CONN_DIR_ALL = 15;   // ConnDirFlags: Up|Down|Left|Right

let Avoid = null;

function routePoints(req) {
  const router = new Avoid.Router(Avoid.RouterFlag.OrthogonalRouting.value);
  const opts = req.options || {};
  if (opts.shapeBufferDistance != null) {
    router.setRoutingParameter(
      Avoid.RoutingParameter.shapeBufferDistance.value, opts.shapeBufferDistance);
  }
  if (opts.idealNudgingDistance != null) {
    router.setRoutingParameter(
      Avoid.RoutingParameter.idealNudgingDistance.value, opts.idealNudgingDistance);
  }

  const shapes = Object.create(null);
  for (const n of req.nodes) {
    const tl = new Avoid.Point(n.x, n.y);
    const br = new Avoid.Point(n.x + n.width, n.y + n.height);
    const shape = new Avoid.ShapeRef(router, new Avoid.Rectangle(tl, br));
    // four side pins sharing one class id; libavoid picks the natural side per connector
    // end (centre-only pins congest shared nodes and inflate crossings).
    for (const [fx, fy] of [[0.5, 0], [0.5, 1], [0, 0.5], [1, 0.5]]) {
      new Avoid.ShapeConnectionPin(shape, CONN_PIN_CENTRE, fx, fy, true, 0, CONN_DIR_ALL);
    }
    shapes[n.id] = shape;
  }

  const conns = [];
  for (const e of req.edges) {
    const s = shapes[e.source];
    const t = shapes[e.target];
    if (!s || !t) continue;
    const conn = new Avoid.ConnRef(
      router, new Avoid.ConnEnd(s, CONN_PIN_CENTRE), new Avoid.ConnEnd(t, CONN_PIN_CENTRE)
    );
    conns.push({ id: e.id, ref: conn });
  }

  router.processTransaction();

  const edges = [];
  for (const c of conns) {
    const route = c.ref.displayRoute();
    const pts = [];
    for (let i = 0; i < route.size(); i++) {
      const p = route.at(i);
      pts.push([p.x, p.y]);
    }
    edges.push({ id: c.id, points: pts });
  }
  router.delete();
  return edges;
}

function respond(obj) {
  process.stdout.write(JSON.stringify(obj) + '\n');
}

function handle(line) {
  let req;
  try {
    req = JSON.parse(line);
  } catch (e) {
    respond({ ok: false, error: 'bad json: ' + e.message });
    return;
  }
  try {
    respond({ id: req.id, ok: true, edges: routePoints(req.route) });
  } catch (e) {
    respond({ id: req.id, ok: false, error: String(e && e.message ? e.message : e) });
  }
}

async function main() {
  const { AvoidLib } = await import(gluePath);
  await AvoidLib.load(wasmPath);
  Avoid = AvoidLib.getInstance();

  let buf = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', (chunk) => {
    buf += chunk;
    let nl;
    while ((nl = buf.indexOf('\n')) >= 0) {
      const line = buf.slice(0, nl).trim();
      buf = buf.slice(nl + 1);
      if (line) handle(line);
    }
  });
  process.stdin.on('end', () => process.exit(0));
  process.stdout.write(JSON.stringify({ ready: true }) + '\n');
}

main().catch((e) => {
  process.stderr.write('libavoid-server fatal: ' + (e && e.stack ? e.stack : e) + '\n');
  process.exit(1);
});
