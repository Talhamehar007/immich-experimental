export interface QualityOption {
  id: string;
  label: string;
  resolutionLabel?: string;
  height?: number;
  width?: number;
  bitrate?: number;
  codec?: string;
  isHls?: boolean;
  levelIndex?: number;
}

export interface SpeedOption {
  label: string;
  rate: number;
}

export type VideoFitMode = 'contain' | 'cover';

export interface VideoStats {
  assetId: string;
  viewport: string;
  optimalResolution: string;
  currentResolution: string;
  droppedFrames: string;
  streamType: string;
  codecs: string;
  currentTime: string;
  duration: string;
  bufferHealth: string;
  volume: string;
  playbackRate: string;
}
