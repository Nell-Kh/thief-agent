"""The Step-0 hardware declaration must describe a real machine.

Rule #24 seals this spec before the first move, and the league's fairness
normalization rewards doing more with less. A declaration of ``cpu_mhz: 0.0,
ram_gb: 0.0`` - which is what the Linux-only probe produced on the Windows
laptop this team plays on - throws away the evidence the bonus is computed from
and is, plainly, not true of any machine.

The Windows and macOS branches cannot execute on the CI platform, so they are
tested the only honest way: by driving the dispatch with fakes and asserting the
fallback ORDER, rather than by asserting a number this host cannot produce.
"""

from __future__ import annotations

import platform

import pytest

from police_thief.shared import sysinfo


def test_the_spec_carries_every_field_step0_seals() -> None:
    """A missing key would be sealed as a silently different declaration."""
    spec = sysinfo.hardware_spec()
    assert set(spec) == {
        "os", "machine", "python", "cpu_cores", "cpu_mhz", "ram_gb", "gpu"
    }


def test_the_spec_is_canonically_serializable() -> None:
    """It is hashed into the Step-0 commitment, so it must be plain JSON types."""
    for value in sysinfo.hardware_spec().values():
        assert isinstance(value, (str, int, float))


def test_this_host_reports_real_cpu_and_memory() -> None:
    """On any platform with a supported probe, zeros are a bug, not a machine."""
    spec = sysinfo.hardware_spec()
    assert spec["cpu_cores"] > 0
    if platform.system() in {"Linux", "Windows", "Darwin"}:
        assert spec["ram_gb"] > 0, (
            "RAM probed as 0.0 - the declaration would claim a machine with no "
            "memory (rule #24 fairness bonus)"
        )


def test_ram_falls_back_from_posix_to_windows_to_macos(monkeypatch) -> None:
    """The dispatch order, driven with fakes so every branch is exercised."""
    def no_posix(_name: str) -> int:
        raise OSError("no sysconf here")

    monkeypatch.setattr(sysinfo.os, "sysconf", no_posix)
    monkeypatch.setattr(sysinfo, "_windows_ram_bytes", lambda: 8 * 1024**3)
    assert sysinfo._total_ram_gb() == 8.0

    monkeypatch.setattr(sysinfo, "_windows_ram_bytes", lambda: 0)
    monkeypatch.setattr(sysinfo, "_sysctl", lambda name: str(4 * 1024**3))
    assert sysinfo._total_ram_gb() == 4.0

    monkeypatch.setattr(sysinfo, "_sysctl", lambda name: "")
    assert sysinfo._total_ram_gb() == 0.0


def test_cpu_mhz_falls_back_from_proc_to_windows_to_macos(monkeypatch, tmp_path) -> None:
    """Same ladder for the clock; the final 0.0 means 'the host would not say'."""
    monkeypatch.chdir(tmp_path)  # no /proc/cpuinfo relative lookups
    monkeypatch.setattr(sysinfo, "_windows_cpu_mhz", lambda: 2400.0)
    monkeypatch.setattr(sysinfo, "_sysctl", lambda name: "")
    if platform.system() != "Linux":
        assert sysinfo._cpu_frequency_mhz() == 2400.0

    monkeypatch.setattr(sysinfo, "_windows_cpu_mhz", lambda: 0.0)
    monkeypatch.setattr(sysinfo, "_sysctl", lambda name: str(3.2e9))
    if platform.system() != "Linux":
        assert sysinfo._cpu_frequency_mhz() == 3200.0


@pytest.mark.parametrize("probe", ["_windows_ram_bytes", "_windows_cpu_mhz"])
def test_the_windows_probes_are_safe_to_call_on_any_platform(probe: str) -> None:
    """They must degrade to zero off-Windows, never raise mid-declaration."""
    assert getattr(sysinfo, probe)() in (0, 0.0)


def test_a_missing_gpu_is_reported_plainly_not_omitted() -> None:
    """League play runs on plain laptops; 'none detected' is the honest answer."""
    assert isinstance(sysinfo._gpu_description(), str)
    assert sysinfo._gpu_description() != ""
