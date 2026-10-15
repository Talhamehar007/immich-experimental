<script lang="ts">
  import { Icon } from '@immich/ui';
  import {
    mdiFastForward10,
    mdiPause,
    mdiPlay,
    mdiRewind10,
    mdiVolumeHigh,
    mdiVolumeLow,
    mdiVolumeMute,
  } from '@mdi/js';

  interface Props {
    showPlayFlash: boolean;
    isPaused: boolean;
    seekFeedback: {
      direction: 'left' | 'right';
      seconds: number;
    } | null;
    isSpeedBoostActive: boolean;
    volumeFeedback: {
      volume: number;
      muted: boolean;
    } | null;
  }

  let { showPlayFlash, isPaused, seekFeedback, isSpeedBoostActive, volumeFeedback }: Props = $props();
</script>

<div class="pointer-events-none absolute inset-0 z-30 flex items-center justify-center overflow-hidden">
  <!-- 2x Speed Hold Pill (Top Center) -->
  {#if isSpeedBoostActive}
    <div
      class="animate-in fade-in zoom-in-95 absolute top-6 left-1/2 -translate-x-1/2 rounded-full border border-white/20 bg-black/75 px-4 py-1 text-xs font-bold tracking-wider text-white shadow-xl backdrop-blur-md"
    >
      <span class="text-amber-400">2x</span> Speed
    </div>
  {/if}

  <!-- Volume Adjustment Toast (Top Center) -->
  {#if volumeFeedback}
    <div
      class="animate-in fade-in absolute top-6 left-1/2 flex -translate-x-1/2 items-center gap-2 rounded-full border border-white/15 bg-black/80 px-3.5 py-1.5 text-xs font-semibold text-white shadow-xl backdrop-blur-md duration-100"
    >
      <Icon
        icon={volumeFeedback.muted || volumeFeedback.volume === 0
          ? mdiVolumeMute
          : volumeFeedback.volume < 0.5
            ? mdiVolumeLow
            : mdiVolumeHigh}
        size="18"
      />
      <div class="h-1.5 w-16 overflow-hidden rounded-full bg-white/20">
        <div
          class="h-full bg-red-600 transition-[width] duration-75"
          style:width="{volumeFeedback.muted ? 0 : Math.round(volumeFeedback.volume * 100)}%"
        ></div>
      </div>
      <span class="w-8 text-right tabular-nums">
        {volumeFeedback.muted ? '0%' : `${Math.round(volumeFeedback.volume * 100)}%`}
      </span>
    </div>
  {/if}

  <!-- Center Play/Pause Flash Animation (YouTube Style) -->
  {#if showPlayFlash}
    <div
      class="animate-out fade-out zoom-out-125 flex size-20 items-center justify-center rounded-full bg-black/60 text-white shadow-2xl backdrop-blur-xs transition-all duration-300"
    >
      <Icon icon={isPaused ? mdiPause : mdiPlay} size="44" />
    </div>
  {/if}

  <!-- Double-Click Seek Ripple (Left: -10s) -->
  {#if seekFeedback?.direction === 'left'}
    <div
      class="backdrop-blur-2xs animate-in fade-in absolute inset-y-0 left-0 flex w-1/3 items-center justify-center rounded-r-full bg-white/10 transition-all duration-300"
    >
      <div class="flex flex-col items-center gap-1 text-white">
        <Icon icon={mdiRewind10} size="42" />
        <span class="text-xs font-bold tabular-nums">
          {seekFeedback.seconds} seconds
        </span>
      </div>
    </div>
  {/if}

  <!-- Double-Click Seek Ripple (Right: +10s) -->
  {#if seekFeedback?.direction === 'right'}
    <div
      class="backdrop-blur-2xs animate-in fade-in absolute inset-y-0 right-0 flex w-1/3 items-center justify-center rounded-l-full bg-white/10 transition-all duration-300"
    >
      <div class="flex flex-col items-center gap-1 text-white">
        <Icon icon={mdiFastForward10} size="42" />
        <span class="text-xs font-bold tabular-nums">
          +{seekFeedback.seconds} seconds
        </span>
      </div>
    </div>
  {/if}
</div>
