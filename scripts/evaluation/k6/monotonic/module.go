package monotonic

import "go.k6.io/k6/v2/js/modules"

func init() { modules.Register("k6/x/clipmonotonic", &rootModule{}) }

// rootModule creates independent mutable state for each virtual user.
type rootModule struct{}

func (*rootModule) NewModuleInstance(_ modules.VU) modules.Instance {
	return &moduleInstance{clock: newTimer()}
}

type moduleInstance struct{ clock *timer }

func (m *moduleInstance) Exports() modules.Exports {
	return modules.Exports{Default: m.clock}
}
