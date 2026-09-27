import { ImageManipulator, SaveFormat } from 'expo-image-manipulator';

// Long edge in pixels. Plenty for reading sign text, and keeps uploads to a few
// hundred KB instead of several MB (the PRD's end-to-end budget is ~3 seconds).
const MAX_EDGE = 1600;
const JPEG_QUALITY = 0.7;

export type PreparedImage = { uri: string; width: number; height: number };

export async function prepareForUpload(photo: PreparedImage): Promise<PreparedImage> {
  let context = ImageManipulator.manipulate(photo.uri);
  if (Math.max(photo.width, photo.height) > MAX_EDGE) {
    context = context.resize(photo.width >= photo.height ? { width: MAX_EDGE } : { height: MAX_EDGE });
  }
  const rendered = await context.renderAsync();
  try {
    const result = await rendered.saveAsync({ compress: JPEG_QUALITY, format: SaveFormat.JPEG });
    return { uri: result.uri, width: result.width, height: result.height };
  } finally {
    rendered.release();
    context.release();
  }
}
