const fs = require("fs");
const path = require("path");
const zlib = require("zlib");

const outDir = path.join(__dirname, "..", "extension", "icons");

function crc32(buf) {
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i++) {
    c ^= buf[i];
    for (let k = 0; k < 8; k++) {
      c = (c >>> 1) ^ (0xedb88320 & -(c & 1));
    }
  }
  return (c ^ 0xffffffff) >>> 0;
}

function pngChunk(type, data) {
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length);
  const typeBuf = Buffer.from(type, "ascii");
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(Buffer.concat([typeBuf, data])));
  return Buffer.concat([len, typeBuf, data, crc]);
}

function createPng(size, paint) {
  const raw = Buffer.alloc((size * 4 + 1) * size);
  for (let y = 0; y < size; y++) {
    const row = y * (size * 4 + 1);
    raw[row] = 0;
    for (let x = 0; x < size; x++) {
      const [r, g, b, a] = paint(x, y, size);
      const i = row + 1 + x * 4;
      raw[i] = r;
      raw[i + 1] = g;
      raw[i + 2] = b;
      raw[i + 3] = a;
    }
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(size, 0);
  ihdr.writeUInt32BE(size, 4);
  ihdr[8] = 8;
  ihdr[9] = 6;
  return Buffer.concat([
    Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]),
    pngChunk("IHDR", ihdr),
    pngChunk("IDAT", zlib.deflateSync(raw)),
    pngChunk("IEND", Buffer.alloc(0)),
  ]);
}

function mix(a, b, t) {
  return a.map((v, i) => Math.round(v + (b[i] - v) * t));
}

function paint(x, y, size) {
  const px = (x + 0.5) / size;
  const py = (y + 0.5) / size;
  const dx = px - 0.5;
  const dy = py - 0.5;

  const radius = 0.22;
  const box = 0.5 - 0.08;
  const qx = Math.max(Math.abs(dx) - box + radius, 0);
  const qy = Math.max(Math.abs(dy) - box + radius, 0);
  const dBox = Math.hypot(qx, qy) - radius;
  if (dBox > 0.02) return [0, 0, 0, 0];

  const edge = Math.max(0, 1 - dBox / 0.02);
  let rgb = mix([30, 64, 175], [67, 56, 202], py);

  const left = px < 0.48;
  if (size <= 16) {
    const bar1 = Math.abs(px - 0.38) < 0.09 && Math.abs(py - 0.5) < 0.22;
    const bar2 = Math.abs(px - 0.62) < 0.09 && Math.abs(py - 0.5) < 0.3;
    if (bar1 || bar2) rgb = mix(rgb, [238, 242, 255], 0.92);
  } else {
    const cone = px > 0.22 && px < 0.36 && Math.abs(dy) < 0.08 + (0.36 - px) * 0.9;
    const body = px > 0.18 && px < 0.27 && Math.abs(dy) < 0.12;
    if (cone || body) rgb = mix(rgb, [238, 242, 255], 0.94);

    if (!left) {
      for (const [cx, rMin, rMax, thick] of [
        [0.4, 0.14, 0.2, 0.03],
        [0.4, 0.24, 0.3, 0.03],
      ]) {
        const dist = Math.hypot(px - cx, py - 0.5);
        if (dist > rMin && dist < rMax && px > cx && Math.abs(py - 0.5) < 0.28 + thick) {
          rgb = mix(rgb, [199, 210, 254], 0.9);
        }
      }
    }
  }

  return [rgb[0], rgb[1], rgb[2], Math.round(255 * edge)];
}

fs.mkdirSync(outDir, { recursive: true });
for (const size of [16, 32, 48, 128]) {
  fs.writeFileSync(path.join(outDir, `icon${size}.png`), createPng(size, paint));
}
console.log("icons written to", outDir);
