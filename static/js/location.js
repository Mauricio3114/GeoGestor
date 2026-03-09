let geoWatchInterval = null;

function enviarLocalizacao(latitude, longitude) {
    fetch("/salvar-localizacao", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            latitude: latitude,
            longitude: longitude
        })
    })
    .then(response => response.json())
    .then(data => {
        console.log("Localização enviada:", data.mensagem);
        const statusBox = document.getElementById("auto-status");
        if (statusBox) {
            statusBox.innerText = "Localização enviada com sucesso às " + new Date().toLocaleTimeString();
        }
    })
    .catch(error => {
        console.error("Erro ao enviar localização:", error);
        const statusBox = document.getElementById("auto-status");
        if (statusBox) {
            statusBox.innerText = "Erro ao enviar localização.";
        }
    });
}

function capturarLocalizacao() {
    if (!navigator.geolocation) {
        alert("Geolocalização não suportada pelo navegador.");
        return;
    }

    navigator.geolocation.getCurrentPosition(
        function(position) {
            const latitude = position.coords.latitude;
            const longitude = position.coords.longitude;

            enviarLocalizacao(latitude, longitude);

            setTimeout(() => {
                window.location.reload();
            }, 1000);
        },
        function() {
            alert("Não foi possível obter sua localização.");
        },
        {
            enableHighAccuracy: true,
            timeout: 15000,
            maximumAge: 0
        }
    );
}

function iniciarAtualizacaoAutomatica() {
    if (!navigator.geolocation) {
        console.log("Geolocalização não suportada.");
        return;
    }

    const statusBox = document.getElementById("auto-status");
    if (statusBox) {
        statusBox.innerText = "Monitoramento automático ativo.";
    }

    function capturarEEnviar() {
        navigator.geolocation.getCurrentPosition(
            function(position) {
                const latitude = position.coords.latitude;
                const longitude = position.coords.longitude;
                enviarLocalizacao(latitude, longitude);
            },
            function(error) {
                console.error("Erro ao obter localização:", error);
                if (statusBox) {
                    statusBox.innerText = "Não foi possível obter a localização automática.";
                }
            },
            {
                enableHighAccuracy: true,
                timeout: 15000,
                maximumAge: 0
            }
        );
    }

    capturarEEnviar();

    if (geoWatchInterval) {
        clearInterval(geoWatchInterval);
    }

    geoWatchInterval = setInterval(capturarEEnviar, 30000);
}