<script lang="ts">
  import { decodeBase64 } from '$lib/utils';
  import { TUNABLES } from '$lib/utils/tunables';
  import type { HTMLCanvasAttributes } from 'svelte/elements';
  import { fade } from 'svelte/transition';
  import { thumbHashToRGBA } from 'thumbhash';

  type Props = HTMLCanvasAttributes & {
    base64ThumbHash: string;
    fadeOut?: boolean;
  };

  const { base64ThumbHash, fadeOut = false, class: className, ...restProps }: Props = $props();

  const {
    IMAGE_THUMBNAIL: { THUMBHASH_FADE_DURATION },
  } = TUNABLES;

  const thumbhashCache = new Map<string, { w: number; h: number; rgba: Uint8Array }>();

  function getDecodedThumbhash(hash: string) {
    let cached = thumbhashCache.get(hash);
    if (!cached) {
      cached = thumbHashToRGBA(decodeBase64(hash));
      if (thumbhashCache.size > 500) {
        const firstKey = thumbhashCache.keys().next().value;
        if (firstKey) {
          thumbhashCache.delete(firstKey);
        }
      }
      thumbhashCache.set(hash, cached);
    }
    return cached;
  }

  function renderThumbhash(node: HTMLCanvasElement, hash: string) {
    const draw = (h: string) => {
      if (!h) {
        return;
      }
      try {
        const ctx = node.getContext('2d');
        if (!ctx) {
          return;
        }
        const { w, h: height, rgba } = getDecodedThumbhash(h);
        node.width = w;
        node.height = height;
        const pixels = ctx.createImageData(w, height);
        pixels.data.set(rgba);
        ctx.putImageData(pixels, 0, 0);
      } catch {
        // ignore invalid hash
      }
    };

    draw(hash);

    return {
      update(newHash: string) {
        draw(newHash);
      },
    };
  }
</script>

<canvas
  use:renderThumbhash={base64ThumbHash}
  class={className}
  out:fade={{ duration: fadeOut ? THUMBHASH_FADE_DURATION : 0 }}
  {...restProps}
></canvas>
