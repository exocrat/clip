// Package monotonic is a proposed per-VU elapsed timer for k6 preparation.
// It is not wired to the workload or approved for measurements.
package monotonic

import (
	"errors"
	"time"
)

// timer retains the time.Time monotonic reading rather than converting it to
// a wall-clock timestamp. Each module instance owns exactly one timer.
type timer struct {
	now    func() time.Time
	start  time.Time
	active bool
}

func newTimer() *timer { return &timer{now: time.Now} }

// Start refuses to replace an active interval.
func (t *timer) Start() error {
	if t.active {
		return errors.New("timer already started")
	}
	t.start = t.now()
	t.active = true
	return nil
}

// Stop returns elapsed milliseconds, resets the timer, and rejects invalid
// ordering or a backwards injected clock. It never exposes an absolute time.
func (t *timer) Stop() (float64, error) {
	if !t.active {
		return 0, errors.New("timer not started")
	}
	d := t.now().Sub(t.start)
	t.active = false
	t.start = time.Time{}
	if d < 0 {
		return 0, errors.New("clock moved backwards")
	}
	return float64(d) / float64(time.Millisecond), nil
}
