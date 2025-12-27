import inspect
from powertrack_sdk import models
from datetime import datetime


def test_alert_trigger_active_triggers():
    triggers = [
        {'id': 1, 'isActive': True},
        {'id': 2, 'isActive': False},
        {'id': 3},
    ]
    at = models.AlertTrigger(key='H1', triggers=triggers)
    active = at.active_triggers
    assert isinstance(active, list)
    assert len(active) == 1
    assert active[0]['id'] == 1


def test_hardware_type_name_property():
    h = models.Hardware(key='H1', name='Device', functionCode=None)
    assert h.type_name == 'Unknown'
    h2 = models.Hardware(key='H2', name='Inv', functionCode=1)
    assert 'Inverter' in h2.type_name
    h3 = models.Hardware(key='H3', name='X', functionCode=999)
    assert h3.type_name == 'Type 999'


def test_modeling_total_capacity_kw():
    md = models.ModelingData(siteId='S1', inverters=[{'inverterKw': 2.5}, {'inverterKw': 3.5}])
    assert md.total_capacity_kw == 6.0


def test_sitelist_basic_behaviors():
    data = [
        {'key': 'S10001', 'name': 'A'},
        {'key': 'S10002', 'name': 'B', 'extra': 'meta'},
    ]
    sl = models.SiteList(data, metadata={'owner': 'me'})
    assert len(sl) == 2
    assert sl.get_by_key('S10001').name == 'A'
    filtered = sl.filter_by_keys(['S10002'])
    assert len(filtered) == 1


def test_chartdata_performance_ratio_and_losses():
    cd = models.ChartData(
        allowSmallBinSize=True,
        binSize=1440,
        currentNowBinIndex=0,
        dataNotAvailable=False,
        durations=[],
        end='2020-01-01',
        errorString='',
        hardwareKeys=[],
        hasAlertMessages=False,
        hasOverriddenQuery=False,
        isCategoryChart=False,
        isSummaryChart=False,
        isUsingDaylightSavings=False,
        key='k',
        lastChanged='',
        lastDataDatetime='',
        namedResults={'energy': 100.0, 'expEnergy': 200.0, 'ageAC': 1},
        renderType=0,
        series=[],
        summaryTable=[],
        start=None,
    )
    assert cd.performance_ratio == 0.5
    losses = cd.losses
    assert 'ageAC' in losses
    assert losses['clipping'] == 0


def test_alert_summary_properties():
    s = models.AlertSummary(hardwareKey='H1', maxSeverity=4, count=2)
    assert s.severity_level == 'critical'
    assert s.has_critical_alerts is True


def test_sitedata_counts():
    hw = models.Hardware(key='H1', name='Device')
    hd = models.HardwareDetails(key='H1', summary=hw, details={})
    at = models.AlertTrigger(key='H1', triggers=[{'isActive': True}, {'isActive': False}])
    sd = models.SiteData(site=models.Site(key='S1'), hardware=[hd], alerts=[at], modeling=None, fetchedAt=datetime.now())
    assert sd.hardware_count == 1
    assert sd.active_alerts_count == 1


def test_dataclass_fields_are_camel_case():
    """Test that all dataclass field names are in camelCase (no underscores)."""
    errors = []
    for name, obj in inspect.getmembers(models):
        if inspect.isclass(obj) and hasattr(obj, '__dataclass_fields__'):
            for field_name in obj.__dataclass_fields__:
                if '_' in field_name:
                    errors.append(f"Field '{field_name}' in dataclass '{obj.__name__}' contains underscore")
    assert not errors, "\n".join(errors)
