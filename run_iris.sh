#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-live}"   # live | sim
SESSION="iris_${MODE}"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORLD="$ROOT/worlds/factory/factory.model"
MODELS="$ROOT/worlds/factory/models"

# Kill existing session if it exists
if tmux has-session -t "$SESSION" 2>/dev/null; then
  tmux kill-session -t "$SESSION"
fi

echo "[tmux] ROOT=$ROOT"
echo "[tmux] MODE=$MODE"
echo "[tmux] SESSION=$SESSION"

tmux new-session -d -s "$SESSION" -c "$ROOT"

# Layout: 2x2 grid
tmux split-window -h -t "$SESSION" -c "$ROOT"
tmux split-window -v -t "$SESSION:0.0" -c "$ROOT"
tmux split-window -v -t "$SESSION:0.1" -c "$ROOT"
tmux select-layout -t "$SESSION" tiled

# Pane indices (after tiled): 0,1,2,3
# We'll use:
# 0 = Gazebo (live only)
# 1 = ROS node (live only)
# 2 = UI
# 3 = spare / logs

if [[ "$MODE" == "live" ]]; then
  # 0) Gazebo
  tmux send-keys -t "$SESSION:0.0" "cd \"$ROOT\"" C-m
  tmux send-keys -t "$SESSION:0.0" "export GAZEBO_MODEL_PATH=\"$MODELS:\${GAZEBO_MODEL_PATH:-}\"" C-m
  tmux send-keys -t "$SESSION:0.0" "echo GAZEBO_MODEL_PATH=\$GAZEBO_MODEL_PATH" C-m
  tmux send-keys -t "$SESSION:0.0" "gazebo \"$WORLD\"" C-m

  # 1) ROS Node
  tmux send-keys -t "$SESSION:0.1" "cd \"$ROOT\"" C-m
  tmux send-keys -t "$SESSION:0.1" "source /opt/ros/humble/setup.zsh" C-m
  tmux send-keys -t "$SESSION:0.1" "export PYTHONPATH=\"$ROOT:\${PYTHONPATH:-}\"" C-m
  tmux send-keys -t "$SESSION:0.1" "which python3 && python3 -c \"import sys; print(sys.executable); import rclpy; print('rclpy OK')\"" C-m
  tmux send-keys -t "$SESSION:0.1" "/usr/bin/python3 src/ros/iris_node.py" C-m

  # 2) UI (PYTHONPATH root)
  tmux send-keys -t "$SESSION:0.2" \
    "cd \"$ROOT\" && export PYTHONPATH=\"$ROOT\" && python3 -m src.ui.app" C-m

  # 3) helper pane
  tmux send-keys -t "$SESSION:0.3" \
    "cd \"$ROOT\" && echo \"LIVE MODE running\" && echo \"Open: http://127.0.0.1:5000/\" && echo \"(This pane is free for logs/tests)\"" C-m

elif [[ "$MODE" == "sim" ]]; then
  # 0) UI only
  tmux send-keys -t "$SESSION:0.0" \
    "cd \"$ROOT\" && export PYTHONPATH=\"$ROOT\" && python3 -m src.ui.app" C-m

  # Other panes can be free
  tmux send-keys -t "$SESSION:0.1" "cd \"$ROOT\" && echo \"SIM MODE\" && echo \"Open: http://127.0.0.1:5000/\"" C-m
  tmux send-keys -t "$SESSION:0.2" "cd \"$ROOT\" && echo \"Free pane\"" C-m
  tmux send-keys -t "$SESSION:0.3" "cd \"$ROOT\" && echo \"Free pane\"" C-m

else
  echo "Usage: ./run_tmux.sh [live|sim]"
  exit 2
fi

tmux attach -t "$SESSION"