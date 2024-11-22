## 1 Upgrade pip :
```bash
pip install --upgrade pip
```

## 2 Create a python environment :
```bash
python3 -m venv .venv
```

## 3 Activate the environment :
```bash
source env/bin/activate
```

## Deactivate the environment :
```bash
deactivate
```

## 4 Install the requirements :
```bash
pip install -r requirements.txt
```

## Update the requirements :
```bash
pip freeze > requirements.txt
```

## 5 Run the server :
```bash
python server.py
```

## Launch docker-compose :
```bash
docker-compose up
```
# To launch a specific service :
```bash
docker-compose up <service_name>
```
## for example to avoid launching the rtsp server that create a rtsp flow for testing :

#### Test : u can access the rtsp test flow using the following link :
```bash
rtsp://localhost:8554/video360
```