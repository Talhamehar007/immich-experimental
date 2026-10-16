<script lang="ts">
  import { Icon } from '@immich/ui';
  import { mdiClose } from '@mdi/js';
  import type { VideoStats } from './types';

  interface Props {
    stats: VideoStats;
    onClose: () => void;
  }

  let { stats, onClose }: Props = $props();
</script>

<div
  class="absolute top-4 left-4 z-40 max-w-sm rounded-lg border border-white/15 bg-black/80 p-3 font-mono text-[11px] leading-tight text-white/90 shadow-2xl backdrop-blur-md select-text"
>
  <div class="mb-2 flex items-center justify-between border-b border-white/10 pb-1.5">
    <div class="flex items-center gap-1.5 font-bold tracking-wide text-white uppercase">
      <span class="inline-block size-2 rounded-full bg-sky-400"></span>
      <span>Stats for nerds</span>
    </div>
    <button
      type="button"
      aria-label="Close stats"
      class="rounded-sm p-0.5 text-white/60 transition-colors hover:bg-white/10 hover:text-white"
      onclick={onClose}
    >
      <Icon icon={mdiClose} size="16" />
    </button>
  </div>

  <div class="grid grid-cols-[110px_1fr] gap-x-2 gap-y-1">
    <span class="text-white/50">Video ID:</span>
    <span class="truncate font-semibold text-white/95">{stats.assetId}</span>

    <span class="text-white/50">Viewport:</span>
    <span>{stats.viewport}</span>

    <span class="text-white/50">Current Res:</span>
    <span class="font-semibold text-emerald-400">{stats.currentResolution}</span>

    <span class="text-white/50">Optimal Res:</span>
    <span>{stats.optimalResolution}</span>

    <span class="text-white/50">Stream Mode:</span>
    <span class="text-yellow-400">{stats.streamType}</span>

    <span class="text-white/50">Codecs:</span>
    <span class="truncate">{stats.codecs}</span>

    <span class="text-white/50">Buffer Health:</span>
    <span class="font-semibold text-sky-400">{stats.bufferHealth}</span>

    <span class="text-white/50">Dropped Frames:</span>
    <span>{stats.droppedFrames}</span>

    <span class="text-white/50">Current Time:</span>
    <span>{stats.currentTime} / {stats.duration}</span>

    <span class="text-white/50">Volume / State:</span>
    <span>{stats.volume}</span>

    <span class="text-white/50">Speed:</span>
    <span>{stats.playbackRate}</span>
  </div>
</div>
