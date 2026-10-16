import { isHttpError, type ApiHttpError } from '@immich/sdk';
import type { HandleClientError } from '@sveltejs/kit';

const DEFAULT_MESSAGE = 'Hmm, not sure about that. Check the logs or open a ticket?';

const parseHTTPError = (httpError: ApiHttpError) => {
  const statusCode = httpError?.status || httpError?.data?.statusCode || 500;
  const message = httpError?.data?.message || (httpError?.data && String(httpError.data)) || httpError?.message;

  console.log({
    status: statusCode,
    response: httpError?.data || 'No data',
  });

  return {
    message: message || DEFAULT_MESSAGE,
    code: statusCode,
    stack: httpError?.stack,
  };
};

const parseError = (error: unknown, status: number, message: string) => {
  if (isHttpError(error)) {
    return parseHTTPError(error);
  }

  return {
    message: (error as Error)?.message || message || DEFAULT_MESSAGE,
    code: status,
  };
};

const isChunkLoadError = (error: unknown): boolean => {
  const message = (error as Error)?.message ?? '';
  return (
    message.includes('Failed to fetch dynamically imported module') ||
    message.includes('Importing a module script failed') ||
    message.includes('error loading dynamically imported module')
  );
};

export const handleError: HandleClientError = ({ error, status, message }) => {
  if (isChunkLoadError(error) && typeof window !== 'undefined') {
    const lastReload = Number(sessionStorage.getItem('immich_chunk_reload_time') || 0);
    const now = Date.now();
    if (now - lastReload > 5000) {
      sessionStorage.setItem('immich_chunk_reload_time', String(now));
      window.location.reload();
      return {
        message: 'Updating application...',
        code: 0,
      };
    }
  }

  const result = parseError(error, status, message);
  console.error(`[hooks.client.ts]:handleError ${result.message}`, error);
  return result;
};
