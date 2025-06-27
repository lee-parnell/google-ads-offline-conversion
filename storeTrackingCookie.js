<script>
(function() {
    function setTrackingCookie(name, value, days) {
        var expires = new Date(Date.now() + (days*24*60*60*1000)).toUTCString()

        document.cookie = [
            encodeURIComponent(name) + '=' + encodeURIComponent(value),
            'Expires' + '=' + encodeURIComponent(expires),
            'Path' + '=' + '/'
        ].join('; ');
}
    var params = new URLSearchParams(window.location.search)
    var gclid = params.get("gclid");
    var gbraid = params.get("gbraid");
    
    if (gclid) setTrackingCookie('_ads_gclid', gclid, 90);
    if (gbraid) setTrackingCookie('_ads_gbraid', gbraid, 90);
})();
</script>
