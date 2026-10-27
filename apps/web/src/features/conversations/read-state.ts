/** Queue read-watermark acknowledgements issued only after a view renders entries. */
export type AcknowledgeRead = (lastDisplayedSequence: number) => Promise<void>;

/**
 * Create the explicit post-render acknowledgement callback used by the conversation UI.
 * Polling/fetch code never calls this function; the view supplies the greatest sequence it
 * has actually displayed. Requests are serialized and never move the watermark backwards.
 */
export function createDisplayedReadAcknowledger(
  acknowledge: AcknowledgeRead,
  initialWatermark = 0,
): (lastDisplayedSequence: number) => Promise<void> {
  if (!Number.isSafeInteger(initialWatermark) || initialWatermark < 0) {
    throw new RangeError('initialWatermark must be a nonnegative safe integer');
  }

  let acknowledgedThrough = initialWatermark;
  let queue: Promise<void> = Promise.resolve();

  return (lastDisplayedSequence) => {
    if (!Number.isSafeInteger(lastDisplayedSequence) || lastDisplayedSequence < 0) {
      return Promise.reject(
        new RangeError('lastDisplayedSequence must be a nonnegative safe integer'),
      );
    }

    const pending = queue.then(async () => {
      if (lastDisplayedSequence <= acknowledgedThrough) return;
      await acknowledge(lastDisplayedSequence);
      acknowledgedThrough = lastDisplayedSequence;
    });
    queue = pending.catch(() => undefined);
    return pending;
  };
}
