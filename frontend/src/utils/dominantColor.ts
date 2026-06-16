export async function getDominantColor(imageUrl: string): Promise<string | null> {
  return new Promise((resolve) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      try {
        // 32×32 gives 4× more samples than 16×16 for better accuracy on complex art.
        const SIZE = 32;
        const canvas = document.createElement('canvas');
        canvas.width = SIZE;
        canvas.height = SIZE;
        const ctx = canvas.getContext('2d');
        if (!ctx) {
          resolve(null);
          return;
        }
        ctx.drawImage(img, 0, 0, SIZE, SIZE);
        const data = ctx.getImageData(0, 0, SIZE, SIZE).data;

        const buckets: Record<
          string,
          { r: number; g: number; b: number; count: number; weight: number }
        > = {};

        for (let i = 0; i < data.length; i += 4) {
          const r = data[i],
            g = data[i + 1],
            b = data[i + 2],
            a = data[i + 3];
          if (a < 128) continue;

          const avg = (r + g + b) / 3;
          // Skip near-black and near-white — they produce unusable accent colors.
          if (avg < 12 || avg > 243) continue;

          // Saturation weight: colorful pixels (yellow, red, blue) count up to 5×
          // more than neutral grays, so the vibrant accent color wins even when grays
          // numerically outnumber it (common in album art with gray backgrounds/text).
          const max = Math.max(r, g, b);
          const min = Math.min(r, g, b);
          const sat = max === 0 ? 0 : (max - min) / max;
          const w = 1 + sat * 4;

          const key = `${r >> 5},${g >> 5},${b >> 5}`;
          if (!buckets[key]) buckets[key] = { r: 0, g: 0, b: 0, count: 0, weight: 0 };
          buckets[key].r += r;
          buckets[key].g += g;
          buckets[key].b += b;
          buckets[key].count++;
          buckets[key].weight += w;
        }

        // Pick the bucket with the highest saturation-weighted score.
        let best: { r: number; g: number; b: number; count: number; weight: number } | null = null;
        for (const bucket of Object.values(buckets)) {
          if (!best || bucket.weight > best.weight) best = bucket;
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
        // SecurityError from CORS-blocked getImageData
        resolve(null);
      }
    };
    img.onerror = () => resolve(null);
    img.src = imageUrl;
  });
}
