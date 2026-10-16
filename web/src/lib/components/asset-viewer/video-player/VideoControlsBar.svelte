<script lang="ts">
  import { Icon } from '@immich/ui';
  import {
    mdiCog,
    mdiCropLandscape,
    mdiFullscreen,
    mdiFullscreenExit,
    mdiPause,
    mdiPictureInPictureBottomRight,
    mdiPlay,
    mdiPlayCircleOutline,
    mdiSkipNext,
    mdiSkipPrevious,
    mdiVolumeHigh,
    mdiVolumeLow,
    mdiVolumeMute,
    mdiWindowMaximize,
  } from '@mdi/js';
  import type { QualityOption, SpeedOption, VideoFitMode } from './types';
  import VideoScrubber from './VideoScrubber.svelte';
  import VideoSettingsMenu from './VideoSettingsMenu.svelte';

  interface Props {
    isPaused: boolean;
    currentTime: number;
    duration: number;
    buffered: TimeRanges | null;
    volume: number;
    isMuted: boolean;
    playbackRate: number;
    fitMode: VideoFitMode;
    isAutoplayNext: boolean;
    isFullscreen: boolean;
    isSettingsOpen: boolean;
    qualities: QualityOption[];
    activeQualityId: string;
    speeds?: SpeedOption[];
    isLooping: boolean;
    isLiveTranscoding: boolean;
    canLiveTranscode: boolean;
    showStatsForNerds: boolean;
    hasPreviousAsset?: boolean;
    hasNextAsset?: boolean;
    onTogglePlay: () => void;
    onPreviousAsset?: () => void;
    onNextAsset?: () => void;
    onSeek: (time: number) => void;
    onScrubStateChange?: (isScrubbing: boolean) => void;
    onVolumeChange: (volume: number) => void;
    onToggleMute: () => void;
    onToggleAutoplayNext: () => void;
    onTogglePiP: () => void;
    onToggleFitMode: () => void;
    onToggleSettings: () => void;
    onCloseSettings: () => void;
    onToggleFullscreen: () => void;
    onSelectSpeed: (speed: number) => void;
    onSelectQuality: (quality: QualityOption) => void;
    onToggleLoop: () => void;
    onToggleLiveTranscoding: () => void;
    onToggleStatsForNerds: () => void;
  }

  let {
    isPaused,
    currentTime,
    duration,
    buffered,
    volume,
    isMuted,
    playbackRate,
    fitMode,
    isAutoplayNext,
    isFullscreen,
    isSettingsOpen,
    qualities,
    activeQualityId,
    speeds,
    isLooping,
    isLiveTranscoding,
    canLiveTranscode,
    showStatsForNerds,
    hasPreviousAsset = false,
    hasNextAsset = false,
    onTogglePlay,
    onPreviousAsset = () => {},
    onNextAsset = () => {},
    onSeek,
    onScrubStateChange = () => {},
    onVolumeChange,
    onToggleMute,
    onToggleAutoplayNext,
    onTogglePiP,
    onToggleFitMode,
    onToggleSettings,
    onCloseSettings,
    onToggleFullscreen,
    onSelectSpeed,
    onSelectQuality,
    onToggleLoop,
    onToggleLiveTranscoding,
    onToggleStatsForNerds,
  }: Props = $props();

  let showRemainingTime = $state(false);

  const formatTime = (seconds: number) => {
    if (Number.isNaN(seconds) || seconds < 0) {
      return '0:00';
    }
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    const sStr = s < 10 ? '0' + s : String(s);
    if (h > 0) {
      const mStr = m < 10 ? '0' + m : String(m);
      return `${h}:${mStr}:${sStr}`;
    }
    return `${m}:${sStr}`;
  };

  const timeDisplay = $derived.by(() => {
    const current = formatTime(currentTime);
    if (showRemainingTime) {
      const remaining = formatTime(Math.max(0, duration - currentTime));
      return `${current} / -${remaining}`;
    }
    const total = formatTime(duration);
    return `${current} / ${total}`;
  });

  const activeQuality = $derived(qualities.find((q) => q.id === activeQualityId) || qualities[0]);

  const isHdOrBetter = $derived.by(() => {
    if (!activeQuality) {
      return false;
    }
    return (
      (activeQuality.height && activeQuality.height >= 720) ||
      activeQuality.label.includes('HD') ||
      activeQuality.label.includes('4K')
    );
  });

  const volumeIcon = $derived.by(() => {
    if (isMuted || volume === 0) {
      return mdiVolumeMute;
    }
    if (volume < 0.5) {
      return mdiVolumeLow;
    }
    return mdiVolumeHigh;
  });
</script>

<div
  class="relative flex w-full flex-col justify-end bg-linear-to-t from-black/90 via-black/50 to-transparent px-3 pt-8 pb-2 text-white transition-opacity duration-200 select-none"
>
  <!-- YouTube Scrubber Bar -->
  <div class="px-1">
    <VideoScrubber {currentTime} {duration} {buffered} {onSeek} {onScrubStateChange} />
  </div>

  <!-- Bottom Buttons Row -->
  <div class="mt-0.5 flex h-10 w-full items-center justify-between gap-1">
    <!-- Left Group -->
    <div class="flex items-center gap-1 sm:gap-1.5">
      <!-- Previous Asset Button -->
      {#if hasPreviousAsset}
        <button
          type="button"
          aria-label="Previous (Shift+P)"
          title="Previous (Shift+P)"
          class="flex size-9 items-center justify-center rounded-full text-white/90 transition-all hover:bg-white/15 hover:text-white active:scale-95"
          onclick={onPreviousAsset}
        >
          <Icon icon={mdiSkipPrevious} size="22" />
        </button>
      {/if}

      <!-- Play / Pause Button -->
      <button
        type="button"
        aria-label={isPaused ? 'Play (k)' : 'Pause (k)'}
        title={isPaused ? 'Play (k)' : 'Pause (k)'}
        class="flex size-9 items-center justify-center rounded-full text-white/90 transition-all hover:bg-white/15 hover:text-white active:scale-95"
        onclick={onTogglePlay}
      >
        <Icon icon={isPaused ? mdiPlay : mdiPause} size="24" />
      </button>

      <!-- Next Asset Button -->
      {#if hasNextAsset}
        <button
          type="button"
          aria-label="Next (Shift+N)"
          title="Next (Shift+N)"
          class="flex size-9 items-center justify-center rounded-full text-white/90 transition-all hover:bg-white/15 hover:text-white active:scale-95"
          onclick={onNextAsset}
        >
          <Icon icon={mdiSkipNext} size="22" />
        </button>
      {/if}

      <!-- Volume Group (Icon + Expandable Horizontal Slider) -->
      <div class="group/volume relative flex items-center">
        <button
          type="button"
          aria-label={isMuted ? 'Unmute (m)' : 'Mute (m)'}
          title={isMuted ? 'Unmute (m)' : 'Mute (m)'}
          class="flex size-9 items-center justify-center rounded-full text-white/90 transition-all hover:bg-white/15 hover:text-white active:scale-95"
          onclick={onToggleMute}
        >
          <Icon icon={volumeIcon} size="22" />
        </button>

        <!-- Slider smoothly expands on hover -->
        <div
          class="flex w-0 items-center overflow-hidden transition-all duration-300 ease-out group-focus-within/volume:w-20 group-hover/volume:w-20"
        >
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            aria-label="Volume"
            value={isMuted ? 0 : volume}
            class="h-1 w-16 cursor-pointer appearance-none rounded-full bg-white/30 accent-sky-500 transition-colors hover:bg-white/50"
            oninput={(e) => onVolumeChange(Number((e.currentTarget as HTMLInputElement).value))}
          />
        </div>
      </div>

      <!-- Time Display (Click toggles total vs remaining) -->
      <button
        type="button"
        title="Toggle remaining time"
        class="rounded-sm px-1.5 py-0.5 text-xs font-medium text-white/90 tabular-nums transition-colors hover:bg-white/15 hover:text-white"
        onclick={() => (showRemainingTime = !showRemainingTime)}
      >
        {timeDisplay}
      </button>
    </div>

    <!-- Right Group -->
    <div class="flex items-center gap-1 sm:gap-1.5">
      <!-- Autoplay Next Toggle -->
      <button
        type="button"
        aria-label={isAutoplayNext ? 'Autoplay is on' : 'Autoplay is off'}
        title={isAutoplayNext ? 'Autoplay is on' : 'Autoplay is off'}
        class="flex size-9 items-center justify-center rounded-full text-white/90 transition-all hover:bg-white/15 hover:text-white active:scale-95 {isAutoplayNext
          ? 'text-sky-400'
          : 'text-white/60'}"
        onclick={onToggleAutoplayNext}
      >
        <Icon icon={mdiPlayCircleOutline} size="22" />
      </button>

      <!-- Picture-in-Picture Button -->
      <button
        type="button"
        aria-label="Miniplayer (i)"
        title="Miniplayer (i)"
        class="hidden size-9 items-center justify-center rounded-full text-white/90 transition-all hover:bg-white/15 hover:text-white active:scale-95 sm:flex"
        onclick={onTogglePiP}
      >
        <Icon icon={mdiPictureInPictureBottomRight} size="20" />
      </button>

      <!-- Theater / Fit Mode Toggle -->
      <button
        type="button"
        aria-label={fitMode === 'cover' ? 'Fit to screen (t)' : 'Fill screen (t)'}
        title={fitMode === 'cover' ? 'Fit to screen (t)' : 'Fill screen (t)'}
        class="flex size-9 items-center justify-center rounded-full text-white/90 transition-all hover:bg-white/15 hover:text-white active:scale-95"
        onclick={onToggleFitMode}
      >
        <Icon icon={fitMode === 'cover' ? mdiWindowMaximize : mdiCropLandscape} size="20" />
      </button>

      <!-- YouTube Settings Gear Button -->
      <div class="relative">
        <button
          type="button"
          aria-label="Settings"
          title="Settings"
          class="relative flex size-9 items-center justify-center rounded-full text-white/90 transition-all hover:bg-white/15 hover:text-white active:scale-95"
          onclick={onToggleSettings}
        >
          <Icon
            icon={mdiCog}
            size="22"
            class="transition-transform duration-300 {isSettingsOpen ? 'rotate-45' : 'hover:rotate-30'}"
          />
          <!-- YouTube HD Badge on Gear Icon -->
          {#if isHdOrBetter}
            <span
              class="px-0.8 py-0.2 absolute -top-0.5 -right-0.5 rounded-sm bg-sky-500 text-[8px] font-black tracking-tight text-white uppercase shadow-sm"
            >
              HD
            </span>
          {/if}
        </button>

        <!-- Settings Popover Menu Component -->
        <VideoSettingsMenu
          isOpen={isSettingsOpen}
          currentSpeed={playbackRate}
          {speeds}
          {qualities}
          {activeQualityId}
          {isLooping}
          {isLiveTranscoding}
          {canLiveTranscode}
          {showStatsForNerds}
          onClose={onCloseSettings}
          {onSelectSpeed}
          {onSelectQuality}
          {onToggleLoop}
          {onToggleLiveTranscoding}
          {onToggleStatsForNerds}
        />
      </div>

      <!-- Fullscreen Button -->
      <button
        type="button"
        aria-label={isFullscreen ? 'Exit fullscreen (f)' : 'Fullscreen (f)'}
        title={isFullscreen ? 'Exit fullscreen (f)' : 'Fullscreen (f)'}
        class="flex size-9 items-center justify-center rounded-full text-white/90 transition-all hover:bg-white/15 hover:text-white active:scale-95"
        onclick={onToggleFullscreen}
      >
        <Icon icon={isFullscreen ? mdiFullscreenExit : mdiFullscreen} size="22" />
      </button>
    </div>
  </div>
</div>
