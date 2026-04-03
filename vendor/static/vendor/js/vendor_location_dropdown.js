document.addEventListener('DOMContentLoaded', function () {
    const citySelect = document.getElementById('id_city');
    const zoneSelect = document.getElementById('id_zone');
    const areaSelect = document.getElementById('id_area');

    if (!citySelect || !zoneSelect || !areaSelect) return;

    // Read the currently saved IDs (set by VendorProfileForm via data attrs)
    const savedCityId = citySelect.value || '';
    const savedZoneId = zoneSelect.dataset.zoneId || zoneSelect.value || '';
    const savedAreaId = areaSelect.dataset.areaId || areaSelect.value || '';

    /**
     * Fetch zones for a given city, populate the zone <select>.
     * If selectValue is provided, that option will be pre-selected.
     */
    function loadZones(cityId, selectValue) {
        zoneSelect.innerHTML = '<option value="">---------</option>';
        areaSelect.innerHTML = '<option value="">---------</option>';
        if (!cityId) return;

        fetch(`/admin/vendor/vendorprofile/ajax/load-zones/?city_id=${cityId}`)
            .then(r => r.json())
            .then(data => {
                data.forEach(function (zone) {
                    const opt = document.createElement('option');
                    opt.value = zone.zone_id;
                    opt.text = zone.zone_name;
                    if (String(zone.zone_id) === String(selectValue)) opt.selected = true;
                    zoneSelect.add(opt);
                });
            });
    }

    /**
     * Fetch areas for a given zone, populate the area <select>.
     * If selectValue is provided, that option will be pre-selected.
     */
    function loadAreas(zoneId, selectValue) {
        areaSelect.innerHTML = '<option value="">---------</option>';
        if (!zoneId) return;

        fetch(`/admin/vendor/vendorprofile/ajax/load-areas/?zone_id=${zoneId}`)
            .then(r => r.json())
            .then(data => {
                data.forEach(function (area) {
                    const opt = document.createElement('option');
                    opt.value = area.area_id;
                    opt.text = area.area_name;
                    if (String(area.area_id) === String(selectValue)) opt.selected = true;
                    areaSelect.add(opt);
                });
            });
    }

    // ── Event listeners ──────────────────────────────────────────────────────
    citySelect.addEventListener('change', function () {
        loadZones(this.value, '');
    });

    zoneSelect.addEventListener('change', function () {
        loadAreas(this.value, '');
    });

    // ── On page load: restore zones/areas for existing records ────────────────
    // Zone dropdown has data-city-id set by the form; use it to restore options.
    const initCityId = zoneSelect.dataset.cityId || '';
    const initZoneId = areaSelect.dataset.zoneId || '';

    if (initCityId) {
        // Edit view – city already selected, reload zones and keep saved zone
        loadZones(initCityId, savedZoneId);

        // After zones load, also reload areas for the saved zone
        if (initZoneId) {
            fetch(`/admin/vendor/vendorprofile/ajax/load-areas/?zone_id=${initZoneId}`)
                .then(r => r.json())
                .then(data => {
                    areaSelect.innerHTML = '<option value="">---------</option>';
                    data.forEach(function (area) {
                        const opt = document.createElement('option');
                        opt.value = area.area_id;
                        opt.text = area.area_name;
                        if (String(area.area_id) === String(savedAreaId)) opt.selected = true;
                        areaSelect.add(opt);
                    });
                });
        }
    }
});
