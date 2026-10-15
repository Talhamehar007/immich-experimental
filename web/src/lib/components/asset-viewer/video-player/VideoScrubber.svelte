<script lang="ts">
  interface Props {
    currentTime: number;
    duration: number;
    buffered: TimeRanges | null;
    onSeek: (time: number) => void;
    onScrubStateChange?: (isScrubbing: boolean) => void;
  }

  let { currentTime, duration, buffered, onSeek, onScrubStateChange = () => {} }: Props = $props();

  let trackElement: HTMLDivElement | undefined = $state();
  let isDragging = $state(false);
  let isHovering = $state(false);
  let hoverX = $state(0);
  let hoverTime = $state(0);
  let dragTime = $state(0);

  const displayTime = $derived(isDragging ? dragTime : currentTime);
  const progressPercent = $derived(duration > 0 ? Math.min(100, Math.max(0, (displayTime / duration) * 100)) : 0);

  const bufferedPercent = $derived.by(() => {
    if (!buffered || buffered.length === 0 || duration <= 0) {
      return 0;
    }
    // Find the buffered range covering current time, or highest buffered end
    let maxBuffered = 0;
    for (let i = 0; i < buffered.length; i++) {
      const end = buffered.end(i);
      if (end > maxBuffered) {
        maxBuffered = end;
      }
    }
    return Math.min(100, Math.max(0, (maxBuffered / duration) * 100));
  });

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

  const getTimeFromPointer = (event: PointerEvent): number => {
    if (!trackElement || duration <= 0) {
      return 0;
    }
    const rect = trackElement.getBoundingClientRect();
    const offsetX = Math.max(0, Math.min(event.clientX - rect.left, rect.width));
    const percent = offsetX / rect.width;
    return percent * duration;
  };

  const handlePointerDown = (event: PointerEvent) => {
    event.preventDefault();
    isDragging = true;
    onScrubStateChange(true);
    trackElement?.setPointerCapture(event.pointerId);
    dragTime = getTimeFromPointer(event);
    onSeek(dragTime);
  };

  const handlePointerMove = (event: PointerEvent) => {
    if (!trackElement || duration <= 0) {
      return;
    }
    const rect = trackElement.getBoundingClientRect();
    const offsetX = Math.max(0, Math.min(event.clientX - rect.left, rect.width));
    hoverX = offsetX;
    hoverTime = (offsetX / rect.width) * duration;

    if (isDragging) {
      dragTime = hoverTime;
      onSeek(dragTime);
    }
  };

  const handlePointerUp = (event: PointerEvent) => {
    if (isDragging) {
      isDragging = false;
      onScrubStateChange(false);
      try {
        trackElement?.releasePointerCapture(event.pointerId);
      } catch {
        // Pointer capture may have been lost
      }
      onSeek(dragTime);
    }
  };

  const handlePointerCancel = (event: PointerEvent) => {
    if (isDragging) {
      isDragging = false;
      onScrubStateChange(false);
      try {
        trackElement?.releasePointerCapture(event.pointerId);
      } catch {
        // Ignore
      }
    }
  };
</script>

<!-- Outer interactive container with increased hit area for smooth scrubbing -->
<div
  bind:this={trackElement}
  role="slider"
  tabindex="0"
  aria-label="Video scrubber"
  aria-valuemin="0"
  aria-valuemax={duration}
  aria-valuenow={displayTime}
  aria-valuetext={formatTime(displayTime)}
  class="group relative flex h-5 w-full cursor-pointer touch-none items-center select-none"
  onpointerdown={handlePointerDown}
  onpointermove={handlePointerMove}
  onpointerup={handlePointerUp}
  onpointercancel={handlePointerCancel}
  onpointerenter={() => (isHovering = true)}
  onpointerleave={() => (isHovering = false)}
>
  <!-- Hover timestamp tooltip (YouTube style pill) -->
  {#if (isHovering || isDragging) && duration > 0}
    <div
      class="pointer-events-none absolute -top-8 z-30 -translate-x-1/2 rounded-sm bg-black/85 px-1.5 py-0.5 text-xs font-semibold text-white tabular-nums shadow-md backdrop-blur-xs transition-opacity duration-150"
      style:left="{hoverX}px"
    >
      {formatTime(hoverTime)}
    </div>
  {/if}

  <!-- Progress Track Container -->
  <div
    class="relative h-1 w-full overflow-hidden rounded-full bg-white/20 transition-all duration-150 group-hover:h-1.5 {isDragging
      ? 'h-1.5!'
      : ''}"
  >
    <!-- Buffered Track -->
    <div
      class="absolute inset-y-0 left-0 bg-white/40 transition-[width] duration-200"
      style:width="{bufferedPercent}%"
    ></div>

    <!-- Hover preview indicator -->
    {#if isHovering && !isDragging}
      <div
        class="absolute inset-y-0 left-0 bg-white/25"
        style:width="{(hoverX / (trackElement?.clientWidth || 1)) * 100}%"
      ></div>
    {/if}

    <!-- Played Track (YouTube Red) -->
    <div
      class="absolute inset-y-0 left-0 bg-red-600 transition-[width] duration-75"
      style:width="{progressPercent}%"
    ></div>
  </div>

  <!-- Scrubber Handle / Thumb (expands on hover/drag like YouTube) -->
  <div
    class="pointer-events-none absolute top-1/2 -translate-1/2 rounded-full bg-red-600 shadow-sm transition-transform duration-150 {isHovering ||
    isDragging
      ? 'scale-100'
      : 'scale-0'}"
    style:left="{progressPercent}%"
    style:width="13px"
    style:height="13px"
  ></div>
</div>
