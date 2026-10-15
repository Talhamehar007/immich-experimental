<script lang="ts">
  import { Icon } from '@immich/ui';
  import {
    mdiCheck,
    mdiChevronLeft,
    mdiChevronRight,
    mdiInformationOutline,
    mdiRepeat,
    mdiSpeedometer,
    mdiTune,
    mdiVideoWireless,
  } from '@mdi/js';
  import type { QualityOption, SpeedOption } from './types';

  interface Props {
    isOpen: boolean;
    currentSpeed: number;
    speeds?: SpeedOption[];
    qualities: QualityOption[];
    activeQualityId: string;
    isLooping: boolean;
    isLiveTranscoding: boolean;
    canLiveTranscode: boolean;
    showStatsForNerds: boolean;
    onClose: () => void;
    onSelectSpeed: (speed: number) => void;
    onSelectQuality: (quality: QualityOption) => void;
    onToggleLoop: () => void;
    onToggleLiveTranscoding: () => void;
    onToggleStatsForNerds: () => void;
  }

  const defaultSpeeds: SpeedOption[] = [
    { label: '0.25x', rate: 0.25 },
    { label: '0.5x', rate: 0.5 },
    { label: '0.75x', rate: 0.75 },
    { label: 'Normal', rate: 1 },
    { label: '1.25x', rate: 1.25 },
    { label: '1.5x', rate: 1.5 },
    { label: '1.75x', rate: 1.75 },
    { label: '2x', rate: 2 },
  ];

  let {
    isOpen,
    currentSpeed,
    speeds = defaultSpeeds,
    qualities,
    activeQualityId,
    isLooping,
    isLiveTranscoding,
    canLiveTranscode,
    showStatsForNerds,
    onClose,
    onSelectSpeed,
    onSelectQuality,
    onToggleLoop,
    onToggleLiveTranscoding,
    onToggleStatsForNerds,
  }: Props = $props();

  let activeView: 'main' | 'quality' | 'speed' = $state('main');

  // Reset to main view whenever menu closes
  $effect(() => {
    if (!isOpen) {
      activeView = 'main';
    }
  });

  const activeQuality = $derived(qualities.find((q) => q.id === activeQualityId) || qualities[0]);

  const speedLabel = $derived.by(() => {
    const match = speeds.find((s) => Math.abs(s.rate - currentSpeed) < 0.01);
    if (match) {
      return match.label;
    }
    return `${currentSpeed.toFixed(2).replace(/\.?0+$/, '')}x`;
  });

  const handleCustomSpeedDelta = (delta: number) => {
    const newSpeed = Math.min(3, Math.max(0.25, Math.round((currentSpeed + delta) * 20) / 20));
    onSelectSpeed(newSpeed);
  };
</script>

{#if isOpen}
  <!-- Backdrop click catcher to close settings -->
  <button
    type="button"
    aria-label="Close settings"
    tabindex="-1"
    class="fixed inset-0 z-40 cursor-default bg-transparent"
    onclick={onClose}
    onkeydown={(e) => e.key === 'Escape' && onClose()}
  ></button>

  <!-- Settings Popover Menu (YouTube Style) -->
  <div
    class="animate-in fade-in zoom-in-95 absolute right-3 bottom-14 z-50 w-72 overflow-hidden rounded-xl border border-white/10 bg-neutral-900/95 py-1 text-sm text-neutral-100 shadow-2xl backdrop-blur-md transition-all duration-150 select-none"
  >
    {#if activeView === 'main'}
      <!-- Main Menu -->
      <div class="flex flex-col">
        <!-- Quality selector row -->
        <button
          type="button"
          class="flex w-full items-center justify-between px-3.5 py-2.5 text-left transition-colors hover:bg-white/10 active:bg-white/15"
          onclick={() => (activeView = 'quality')}
        >
          <div class="flex items-center gap-2.5">
            <Icon icon={mdiTune} size="18" class="text-neutral-400" />
            <span class="font-medium">Quality</span>
          </div>
          <div class="flex items-center gap-1 text-xs text-neutral-400">
            <span class="max-w-28 truncate">{activeQuality?.label ?? 'Auto'}</span>
            <Icon icon={mdiChevronRight} size="18" />
          </div>
        </button>

        <!-- Playback speed row -->
        <button
          type="button"
          class="flex w-full items-center justify-between px-3.5 py-2.5 text-left transition-colors hover:bg-white/10 active:bg-white/15"
          onclick={() => (activeView = 'speed')}
        >
          <div class="flex items-center gap-2.5">
            <Icon icon={mdiSpeedometer} size="18" class="text-neutral-400" />
            <span class="font-medium">Playback speed</span>
          </div>
          <div class="flex items-center gap-1 text-xs text-neutral-400">
            <span>{speedLabel}</span>
            <Icon icon={mdiChevronRight} size="18" />
          </div>
        </button>

        <!-- Live Transcoding toggle row (if server supports or available) -->
        {#if canLiveTranscode}
          <button
            type="button"
            class="flex w-full items-center justify-between px-3.5 py-2.5 text-left transition-colors hover:bg-white/10 active:bg-white/15"
            onclick={onToggleLiveTranscoding}
          >
            <div class="flex items-center gap-2.5">
              <Icon icon={mdiVideoWireless} size="18" class="text-neutral-400" />
              <div class="flex flex-col">
                <span class="font-medium">Live Transcoding</span>
                <span class="text-[10px] text-neutral-400">Adaptive HLS streaming</span>
              </div>
            </div>
            <!-- Toggle Pill Switch -->
            <div
              class="relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out {isLiveTranscoding
                ? 'bg-red-600'
                : 'bg-neutral-700'}"
            >
              <span
                class="pointer-events-none inline-block size-4 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out {isLiveTranscoding
                  ? 'translate-x-4'
                  : 'translate-x-0'}"
              ></span>
            </div>
          </button>
        {/if}

        <!-- Loop toggle row -->
        <button
          type="button"
          class="flex w-full items-center justify-between px-3.5 py-2.5 text-left transition-colors hover:bg-white/10 active:bg-white/15"
          onclick={onToggleLoop}
        >
          <div class="flex items-center gap-2.5">
            <Icon icon={mdiRepeat} size="18" class="text-neutral-400" />
            <span class="font-medium">Loop video</span>
          </div>
          <!-- Toggle Pill Switch -->
          <div
            class="relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out {isLooping
              ? 'bg-red-600'
              : 'bg-neutral-700'}"
          >
            <span
              class="pointer-events-none inline-block size-4 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out {isLooping
                ? 'translate-x-4'
                : 'translate-x-0'}"
            ></span>
          </div>
        </button>

        <div class="my-1 border-t border-white/10"></div>

        <!-- Stats for nerds row -->
        <button
          type="button"
          class="flex w-full items-center justify-between px-3.5 py-2.5 text-left transition-colors hover:bg-white/10 active:bg-white/15"
          onclick={onToggleStatsForNerds}
        >
          <div class="flex items-center gap-2.5">
            <Icon icon={mdiInformationOutline} size="18" class="text-neutral-400" />
            <span class="font-medium">Stats for nerds</span>
          </div>
          <!-- Toggle Pill Switch -->
          <div
            class="relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out {showStatsForNerds
              ? 'bg-red-600'
              : 'bg-neutral-700'}"
          >
            <span
              class="pointer-events-none inline-block size-4 transform rounded-full bg-white shadow-sm ring-0 transition duration-200 ease-in-out {showStatsForNerds
                ? 'translate-x-4'
                : 'translate-x-0'}"
            ></span>
          </div>
        </button>
      </div>
    {:else if activeView === 'quality'}
      <!-- Quality Submenu -->
      <div class="flex flex-col">
        <button
          type="button"
          class="flex items-center gap-2 border-b border-white/10 px-3 py-2 text-left text-xs font-semibold tracking-wider text-neutral-400 uppercase hover:bg-white/5"
          onclick={() => (activeView = 'main')}
        >
          <Icon icon={mdiChevronLeft} size="18" />
          <span>Quality</span>
        </button>
        <div class="max-h-64 overflow-y-auto py-1">
          {#each qualities as quality (quality.id)}
            {@const isSelected = quality.id === activeQualityId}
            <button
              type="button"
              class="flex w-full items-center justify-between px-3.5 py-2 text-left transition-colors hover:bg-white/10 active:bg-white/15 {isSelected
                ? 'font-medium text-red-500'
                : 'text-neutral-200'}"
              onclick={() => {
                onSelectQuality(quality);
                activeView = 'main';
              }}
            >
              <div class="flex items-center gap-2">
                <span class="text-sm">{quality.label}</span>
                {#if quality.resolutionLabel}
                  <span class="py-0.2 rounded-sm bg-white/10 px-1 text-[10px] font-semibold text-neutral-300">
                    {quality.resolutionLabel}
                  </span>
                {/if}
              </div>
              {#if isSelected}
                <Icon icon={mdiCheck} size="18" class="text-red-500" />
              {/if}
            </button>
          {/each}
        </div>
      </div>
    {:else if activeView === 'speed'}
      <!-- Playback Speed Submenu -->
      <div class="flex flex-col">
        <button
          type="button"
          class="flex items-center gap-2 border-b border-white/10 px-3 py-2 text-left text-xs font-semibold tracking-wider text-neutral-400 uppercase hover:bg-white/5"
          onclick={() => (activeView = 'main')}
        >
          <Icon icon={mdiChevronLeft} size="18" />
          <span>Playback speed</span>
        </button>

        <!-- Custom Speed Stepper / Slider -->
        <div class="flex items-center justify-between border-b border-white/10 px-3.5 py-2">
          <span class="text-xs text-neutral-400">Custom fine-tuning</span>
          <div class="flex items-center gap-1.5">
            <button
              type="button"
              class="flex size-6 items-center justify-center rounded-sm bg-white/10 text-xs font-bold hover:bg-white/20 active:scale-95"
              onclick={() => handleCustomSpeedDelta(-0.05)}
            >
              -
            </button>
            <span class="w-12 text-center text-xs font-semibold text-red-500 tabular-nums">
              {currentSpeed.toFixed(2)}x
            </span>
            <button
              type="button"
              class="flex size-6 items-center justify-center rounded-sm bg-white/10 text-xs font-bold hover:bg-white/20 active:scale-95"
              onclick={() => handleCustomSpeedDelta(0.05)}
            >
              +
            </button>
          </div>
        </div>

        <div class="max-h-60 overflow-y-auto py-1">
          {#each speeds as speed (speed.rate)}
            {@const isSelected = Math.abs(speed.rate - currentSpeed) < 0.01}
            <button
              type="button"
              class="flex w-full items-center justify-between px-3.5 py-2 text-left transition-colors hover:bg-white/10 active:bg-white/15 {isSelected
                ? 'font-medium text-red-500'
                : 'text-neutral-200'}"
              onclick={() => {
                onSelectSpeed(speed.rate);
                activeView = 'main';
              }}
            >
              <span class="text-sm">{speed.label}</span>
              {#if isSelected}
                <Icon icon={mdiCheck} size="18" class="text-red-500" />
              {/if}
            </button>
          {/each}
        </div>
      </div>
    {/if}
  </div>
{/if}
