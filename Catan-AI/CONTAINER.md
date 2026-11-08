# Play Catan through a forwarded port

The repository's `.devcontainer/devcontainer.json` adds a virtual Linux desktop
using the official Dev Containers `desktop-lite` feature. noVNC makes that desktop
available in your browser on forwarded port **6080**. Pygame still runs inside
the container; no local Python or game rebuild is needed.

## Set up the repository container

1. Pull the latest `codex/catan-gameplay-fixes` branch.
2. Open **agent-arena itself** as the VS Code workspace folder.
3. Run **Dev Containers: Rebuild and Reopen in Container** from the command palette
   (or **Rebuild Container** if this repository already owns your container).
4. Wait for the feature installation and `postCreateCommand` to finish. It creates
   `Catan-AI/.venv-container` and installs the gameplay and test dependencies.
5. In VS Code's **Ports** tab, open **6080 — Catan desktop (noVNC)** in your browser.
   If it is not listed, choose **Forward a Port** and enter **6080**.
6. Click **Connect** and enter the desktop password: **vscode**.
7. From the repository root, launch:

   ```sh
   bash Catan-AI/scripts/play-container.sh --name Michael
   ```

   Or, if your terminal is already in `Catan-AI/code`:

   ```sh
   bash ../scripts/play-container.sh --name Michael
   ```

The board appears inside the browser desktop. Click a highlighted intersection
for your first settlement, then a road. The game is you against three AI players.
In noVNC, choose **Settings → Scaling Mode → Local Scaling** if the desktop does
not fit your browser. The virtual desktop is 1440×1000 to fit the full game window.
Closing the browser disconnects the viewer; close the game window or press Ctrl+C
in its launching terminal to stop the game.

## If your existing container belongs to a parent workspace

Your terminal may show a path such as `/workspaces/python/agent-arena`. If VS Code
opened the parent `python` workspace, its devcontainer configuration controls the
container. Simply rebuilding it will NOT read this nested repository's configuration.
Either open `agent-arena` separately using the steps above, or merge the following
settings into the **parent workspace's active** `.devcontainer/devcontainer.json`:

```json
{
  "features": {
    "ghcr.io/devcontainers/features/desktop-lite:1": {
      "password": "vscode",
      "webPort": "6080",
      "vncPort": "5901"
    }
  },
  "forwardPorts": [6080],
  "portsAttributes": {
    "6080": { "label": "Catan desktop (noVNC)", "onAutoForward": "notify" }
  },
  "containerEnv": {
    "VNC_RESOLUTION": "1440x1000x24",
    "VNC_PASSWORD": "vscode",
    "SDL_AUDIODRIVER": "dummy"
  }
}
```

Merge these entries with existing features, ports, and environment variables;
do not replace the parent configuration. The feature supports Debian/Ubuntu-based
containers. Rebuild the parent container, then from `agent-arena` run:

```sh
bash .devcontainer/setup.sh
bash Catan-AI/scripts/play-container.sh --name Michael
```

## Ports, display, and environment

- Forward **6080**, not the game process. Use the URL VS Code opens; if local port
  6080 is occupied, VS Code may select another local port.
- Keep the forwarded desktop port private/local. The configured `vscode` password
  is a development default, not a credential for a publicly shared desktop.
- No Docker host port is published by this configuration. Raw VNC port 5901 is
  not forwarded; browser access uses noVNC.
- The feature sets `DISPLAY=:1` and starts its services on container startup.
  The launch script checks the display and clears dummy-video mode used by tests.
- No sound is needed by this game; dummy audio avoids unavailable container audio
  devices. Video uses X11, not SDL's dummy renderer.
- The launch script works from any working directory and always uses the dedicated
  container environment, regardless of an already activated `.venv`.
- After changing Python/container versions, remove only `Catan-AI/.venv-container`
  and rerun setup if that environment has become incompatible. Your existing
  `.venv` is not touched by the setup script.

You can also activate the dedicated environment and use the original command:

```sh
cd Catan-AI
source .venv-container/bin/activate
python code/catanGame.py --name Michael
```

If the browser desktop does not load, confirm you rebuilt the correct workspace,
check that port 6080 is forwarded, and inspect `/tmp/container-init.log` inside
the container. If Catan only prints a Pygame banner, check `echo "$DISPLAY"` and
`xdpyinfo -display :1`; run the launch script for an explicit display diagnostic.

Feature documentation: https://github.com/devcontainers/features/tree/main/src/desktop-lite
