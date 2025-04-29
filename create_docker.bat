# Imposta il percorso del progetto e il nome dell'immagine Docker
$projectPath = "D:\Progetti\BF_personaltune"
$imageName = "bf_personaltune:latest"

# Controlla se Docker è in esecuzione
$dockerStatus = Get-Service -Name "com.docker.service" -ErrorAction SilentlyContinue
if ($dockerStatus.Status -ne "Running") {
    Write-Host "Docker non è in esecuzione. Avvialo manualmente e riprova."
    exit 1
}

# Crea il Dockerfile se non esiste
$dockerfilePath = "$projectPath\Dockerfile"
if (!(Test-Path $dockerfilePath)) {
    Write-Host "Creazione del Dockerfile..."
    @"
    FROM python:3.9
    WORKDIR /app
    COPY . .
    RUN pip install -r requirements.txt
    CMD ["python", "main.py"]
    "@ | Out-File -Encoding utf8 $dockerfilePath
    Write-Host "Dockerfile creato con successo."
}

# Spostati nella directory del progetto
Set-Location -Path $projectPath

# Costruisce l'immagine Docker
Write-Host "Costruzione dell'immagine Docker..."
docker build -t $imageName .
if ($LASTEXITCODE -ne 0) {
    Write-Host "Errore nella costruzione dell'immagine Docker. Controlla il Dockerfile."
    exit 1
}

# Esegue il container Docker
Write-Host "Avvio del container Docker..."
docker run --rm -it -v "$projectPath:/app" -p 8080:8080 $imageName
if ($LASTEXITCODE -ne 0) {
    Write-Host "Errore nell'avvio del container Docker. Controlla la configurazione."
    exit 1
}

Write-Host "Container avviato con successo!"
