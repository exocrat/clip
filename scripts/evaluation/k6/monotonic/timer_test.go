package monotonic

import (
	"testing"
	"time"
)

func TestTimerOrderingAndReset(t *testing.T) {
	current := time.Unix(100, 0)
	timer := &timer{now: func() time.Time { return current }}
	if _, err := timer.Stop(); err == nil {
		t.Fatal("stop without start accepted")
	}
	if err := timer.Start(); err != nil {
		t.Fatal(err)
	}
	if err := timer.Start(); err == nil {
		t.Fatal("double start accepted")
	}
	current = current.Add(1250 * time.Microsecond)
	if got, err := timer.Stop(); err != nil || got != 1.25 {
		t.Fatalf("got %v, %v", got, err)
	}
	if _, err := timer.Stop(); err == nil {
		t.Fatal("second stop accepted")
	}
	if err := timer.Start(); err != nil {
		t.Fatal(err)
	}
	current = current.Add(-time.Second)
	if _, err := timer.Stop(); err == nil {
		t.Fatal("backwards clock accepted")
	}
	if err := timer.Start(); err != nil {
		t.Fatal("error did not reset timer")
	}
}

func TestModuleInstancesAreIsolated(t *testing.T) {
	root := &rootModule{}
	a := root.NewModuleInstance(nil).(*moduleInstance)
	b := root.NewModuleInstance(nil).(*moduleInstance)
	if a.clock == b.clock {
		t.Fatal("shared timer")
	}
	if err := a.clock.Start(); err != nil {
		t.Fatal(err)
	}
	if _, err := b.clock.Stop(); err == nil {
		t.Fatal("second instance inherited start")
	}
	if _, err := a.clock.Stop(); err != nil {
		t.Fatal(err)
	}
}
