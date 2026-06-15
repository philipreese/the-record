export async function getDominantColor(imageUrl: string): Promise<string | null> {
  return new Promise((resolve) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      try {
        const canvas = document.createElement('canvas');
        canvas.width = 16;
        canvas.height = 16;
        const ctx = canvas.getContext('2d');
        if (!ctx) {
          resolve(null);
          return;
        }
        ctx.drawImage(img, 0, 0, 16, 16);
        const data = ctx.getImageData(0, 0, 16, 16).data;

        const buckets: Record<string, { r: number; g: number; b: number; count: number }> = {};
        for (let i = 0; i < data.length; i += 4) {
          const r = data[i],
            g = data[i + 1],
            b = data[i + 2],
            a = data[i + 3];
          if (a < 128) continue;
          const key = `${r >> 5},${g >> 5},${b >> 5}`;
          if (!buckets[key]) buckets[key] = { r: 0, g: 0, b: 0, count: 0 };
          buckets[key].r += r;
          buckets[key].g += g;
          buckets[key].b += b;
          buckets[key].count++;
        }

        let best: { r: number; g: number; b: number; count: number } | null = null;
        for (const bucket of Object.values(buckets)) {
          const avg = (bucket.r + bucket.g + bucket.b) / (3 * bucket.count);
          if (avg < 20 || avg > 235) continue;
          if (!best || bucket.count > best.count) best = bucket;
        }

        if (!best) {
          resolve(null);
          return;
        }
        const toHex = (n: number) =>
          Math.round(n / best!.count)
            .toString(16)
            .padStart(2, '0');
        resolve(`#${toHex(best.r)}${toHex(best.g)}${toHex(best.b)}`);
      } catch {
        // SecurityError from CORS-blocked getImageData — no glow, not an error
        resolve(null);
      }
    };
    img.onerror = () => resolve(null);
    img.src = imageUrl;
  });
}
