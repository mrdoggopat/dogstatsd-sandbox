<h1>Setting up Dogstatsd in Kubernetes using both UDP and UDS from scratch</h1>

This sandbox goes over how to submit your own custom metrics via Dogstatsd in your Kubernetes environment. We are going to go over two ways to do this, UDP (User Datagram Protocol) and UDS (Unix Domain Socket). This sandbox will use two very simple python applications to demonstrate this.

<h1>Prerequisites</h1>

A personal Kubernetes cluster. I’d recommend using either Minikube:

Minikube and Docker Desktop, preferred if already ran `minikube start`.

Kubectl, the Kubernetes command line tool. You can install it with homebrew.

Helm set up and preferably the Datadog agent pods deployed.

Python3, with `venv`.

Navigate to a directory of your choice (I’d recommend an empty folder for this project), and set up your Python virtual environment with this command:

```
python3 -m venv ./venv
```

This creates a virtual environment in the /venv folder of your directory. A virtual environment is important for keeping your global Python installation clean. Once you’ve made it, enter the virtual environment with:

```
source ./venv/bin/activate
```

If it worked, you should see a (venv) note before your terminal. This will keep our pip dependencies clean when we generate them.

Technically there is an easier approach with this since we do not require a lot of dependencies since we are using very simple python scripts but as a newbie that I am with Python, I'll stick using `venv` as I am taking a page out of Steven Wenzels APM Containers sandbox :P

<h1>Dogstatsd with UDP (User Datagram Protocol)</h1>

<h3>Step 1: Build the app</h3>

Create a directory to store your files.

Create a python file called `app.py`.

Make sure you install the Dogstatsd client using this command:
```
pip install datadog
```

This is a very simple python app that submits metrics via Dogstatsd via UDP:
```
from datadog import initialize, statsd
import time

options = {
    'statsd_host':'127.0.0.1',
    'statsd_port':8125
}

initialize(**options)

while(1):
  statsd.increment('containerspod.isthebest', tags=["environment:lowkey"])
  statsd.decrement('failedatdoing.ecsfargatelogging', tags=["environment:sad"])
  time.sleep(10)
```

If you have a host agent installed you can actually run this app and validate that the metric submission is working by checking your Metrics Explorer in your Datadog account by running:

```
python3 app.py
```

For the next step, run this command to create a file with all of the python dependencies needed to build the container image:

```
pip freeze > requirements.txt
```

<h3>Step 2: Build the container image</h3>

Create a Docker file and provide these commands in your Dockerfile:

```
FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./app.py

CMD ["python", "app.py"]
```

Make sure that this file is in the same directory as your app.

Run this command preferably in a separate terminal to build the container in Minikube’s Docker daemon:

```
eval $(minikube docker-env)
```

That way we do not need to go through the trouble of pushing the image to the Docker registry (up to you if you want to do that instead).

Note: This eval command is with respect to your current terminal session/tab. If you are using multiple tabs or close out this tab, your terminal session default to your normal Docker image cache instead of Minikube’s Docker image cache.

Then run:

```
docker build -t <your_image_name> .
```

This will build an image with the name `<your_image_name>:latest`.

<h3>Step 3: Kubernetes time :D</h3>

Make sure you are in the minikube context by running:

```
kubectl config current-context
```

Create a manifest YAML file with a name of your choosing or `dogstatsd.yaml`:

```
apiVersion: v1
kind: Pod
metadata:
  name: mydogstatsdpod
spec:
  hostNetwork: true
  containers:
  - name: mydogstatsdpod
    image: <your_image_name>:latest
    imagePullPolicy: IfNotPresent
    env:
    - name: DD_AGENT_HOST
      valueFrom:
          fieldRef:
              fieldPath: status.hostIP
```

After that run the following to deploy the pod:

```
kubectl apply -f dogstatsd.yaml
```

Note: If you make changes in the YAML file after you deployed this pod, you need to delete the pod and redeploy this to work.

Once that is done, create a `values.yaml` with the following:

```
datadog:
  clusterName: <your_cluster_name>
  kubelet:
    tlsVerify: false

  dogstatsd:
    port: 8125
    useHostPort: true
    nonLocalTraffic: true
```

Later versions of the Datadog Helm chart may not even require these configs to be set in the Helm chart, but I put it here just to be safe :P

Note: For minikube, its important to note that the network plugin for Minikube doesn’t support `hostPorts`, so we add `hostNetwork: true` in our pod manifest above. This shares the network namespace of your host with the Datadog Agent. It also means that all ports opened on the container are opened on the host. If a port is used both on the host and in your container, they conflict (since they share the same network namespace) and the pod does not start. Some Kubernetes installations do not allow this.

If you do not have the agent pods deployed yet, run:

```
helm install <RELEASE_NAME> -f values.yaml --set datadog.site="datadoghq.com" --set datadog.apiKey=<YOUR_API_KEY> --set datadog.appKey=<YOUR_APP_KEY> datadog/datadog
```

If you do have the agent pods already deployed, run:

```
helm upgrade <RELEASE_NAME> -f values.yaml --set datadog.site="datadoghq.com" --set datadog.apiKey=<YOUR_API_KEY> --set datadog.appKey=<YOUR_APP_KEY> datadog/datadog
```

After waiting until the pods have successfully spun up (hopefully), verify that the metrics are reporting in your Metrics Explorer.

---

<h1>Dogstatsd with UDS (Unix Domain Socket)</h1>

<h3>Step 1: Build the app</h3>

Before you start, it is recommended to create a separate directory to store the files separately.

Create a python file called `app.py`.

Make sure you install the Dogstatsd client using this command:
```
pip install datadog
```

This is a very simple python app that submits metrics via Dogstatsd via UDS:
```
from datadog import initialize, statsd
import time

options = {
    "statsd_socket_path": "/var/run/datadog/dsd.socket",
}

initialize(**options)

while(1):
  statsd.increment('dogstatsd.kickedmybutt', tags=["environment:lowkey"])
  statsd.decrement('ineedtoget.fourtyticketsolves', tags=["environment:sad"])
  time.sleep(10)
```

The difference here is that we use a socket path to send custom metrics rather than through port 8125. The above configuration was done referencing this Github doc on the Python Dogstatsd client library: https://github.com/DataDog/datadogpy#instantiate-the-dogstatsd-client-with-uds

If you have a host agent installed you can run this app and validate that the metric submission is working by checking your Metrics Explorer in your Datadog account by running:

```
python3 app.py
```

For the next step, run this command to create a file with all of the python dependencies needed to build the container image:

```
pip freeze > requirements.txt
```

<h3>Step 2: Build the container image</h3>

Create a Dockerfile and provide these commands in your Dockerfile:

```
FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./app.py

CMD ["python", "app.py"]
```

Make sure that this file is in the same directory as your app.

Run this command preferably in a separate terminal to build the container in Minikube’s Docker daemon:

```
eval $(minikube docker-env)
```

That way we do not need to go through the trouble of pushing the image to the Docker registry (up to you if you want to do that instead).

Then run (choose a different image name so you do not override previous Dogstatsd image!!!):

```
docker build -t <your_image_name> .
```

<h3>Step 3: Kubernetes time :D</h3>

Create a manifest YAML file with a name of your choosing or `dogstatsd.yaml`:

```
apiVersion: v1
kind: Pod
metadata:
  name: myudsdogstatsd
spec:
  hostPID: true
  containers:
  - name: myudsdogstatsd
    image: <your_image_name>:latest
    imagePullPolicy: IfNotPresent
    env:
      - name: DD_ENTITY_ID
        valueFrom:
          fieldRef:
            fieldPath: metadata.uid
    volumeMounts:
    - name: dsdsocket
      mountPath: /var/run/datadog
      readOnly: true
  volumes:
    - hostPath:
          path: /var/run/datadog/
      name: dsdsocket
```

Notice that we would need to create the volume and volume mounts with the path `var/run/datadog` to match the socket path we set in our `app.py`. If you want to set up origin detection, make sure that `hostPID: true` is set under `spec:`.

After that run the following to deploy the pod:

```
kubectl apply -f udsdogstatsd.yaml
```

Note: If you make changes in the YAML file after you deployed this pod, you need to delete the pod and redeploy this to work.

Once that is done, update your `values.yaml` with the following (keep the existing UDP configs along with your UDS configs):

```
datadog:
  clusterName: <your_cluster_name>
  kubelet:
    tlsVerify: false

  dogstatsd:
    #UDP
    port: 8125
    useHostPort: true
    nonLocalTraffic: true
    
    #UDS
    originDetection: true
    tagCardinality: low
    useSocketVolume: true
    socketPath: /var/run/datadog/dsd.socket
    hostSocketPath: /var/run/datadog/
    useHostPID: true
```

Later versions of the Datadog Helm chart may not even require these configs to be set in the Helm chart, but I put it here just to be safe :P

Note: See that the `socketPath` is set to `/var/run/datadog/dsd.socket` and `hostSocketPath` is set to `var/run/datadog/`. Make sure that this matches with the socket path set in `app.py`. Also, you can technically use a different path, it just has to match with the socket path set in `app.py`.

Run the following to upgrade your Helm chart.

```
helm upgrade <RELEASE_NAME> -f values.yaml --set datadog.site="datadoghq.com" --set datadog.apiKey=<YOUR_API_KEY> --set datadog.appKey=<YOUR_APP_KEY> datadog/datadog
```

After waiting until the pods have successfully spun up (hopefully), verify that the metrics are reporting in your Metrics Explorer.

---

<h1>Extra challenges</h1>

If you feel like a top dawg you can try some of this:

- Can you try and submit custom events via Dogstatsd in both UDP and UDS?
- Can you try and submit other metric types via Dogstatsd in both UDP and UDS? (e.g. Histogram, Gauge, etc)
- Perhaps using another supported language?

---

<h1>Key things to remember</h1>

A misconception I had was assuming that the customer is using UDP just by looking at this section of the agent status output:

```
=========
DogStatsD
=========
  Event Packets: 0
  Event Parse Errors: 0
  Metric Packets: 219,605
  Metric Parse Errors: 0
  Service Check Packets: 0
  Service Check Parse Errors: 0
  Udp Bytes: 18,143,870
  Udp Packet Reading Errors: 0
  Udp Packets: 109,742
  Uds Bytes: 2,169,887
  Uds Origin Detection Errors: 0
  Uds Packet Reading Errors: 0
  Uds Packets: 5,157
  Unterminated Metric Errors: 0
```

In the agent.log, these logs are indication that Dogstatsd is working as intended, but even if the customer is using only UDP or UDS these two logs may show since the later Helm chart versions tends to have both enabled by default without any configuration on the customer's end:

```
# UDP
2023-03-03 14:30:37 UTC | CORE | INFO | (pkg/dogstatsd/listeners/udp.go:95 in Listen) | dogstatsd-udp: starting to listen on [::]:8125

# UDS
2023-03-03 14:30:37 UTC | CORE | INFO | (pkg/dogstatsd/listeners/uds_common.go:146 in Listen) | dogstatsd-uds: starting to listen on /var/run/datadog/dsd.socket
```

It is still recommended to verify the customer which protocol they are using. You can also check their `envvars.log` in their flare for the following environment variables:

```
#For UDP:
DD_DOGSTATSD_PORT
DD_DOGSTATSD_NON_LOCAL_TRAFFIC

#For UDS:
DD_DOGSTATSD_SOCKET
DD_DOGSTATSD_ORIGIN_DETECTION #not required to have UDS working, could be useful for cases where customers are missing certain tags
DD_DOGSTATSD_TAG_CARDINALITY #not required to have UDS working, could be useful for cases where customers are missing certain tags
```

If customer is using UDS, make sure that they have the correct volumes and volume mounts set in their application pod/deployment. If customer is using the DaemonSet approach to set this up, check that they have the volume and volume mounts set in the agent container as well in the DaemonSet:

```
volumeMounts:
    - name: dsdsocket
      mountPath: /var/run/datadog
      readOnly: true
    ## ...
volumes:
    - hostPath:
          path: /var/run/datadog/
      name: dsdsocket
```

Make sure these paths match in the agent container as well as their application pod/deployment manifest.

Some dogstatsd metrics that can be useful for troubleshooting: https://docs.datadoghq.com/developers/dogstatsd/high_throughput/#client-side-telemetry

Getting TRACE level agent flares can be useful for this as well.

Getting the customer's code for submitting their custom metrics can be a good step as well.
