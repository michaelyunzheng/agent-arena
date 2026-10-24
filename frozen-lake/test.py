
import gymnasium as gym
import time

env = gym.make(
    "FrozenLake-v1",
    map_name="4x4",
    is_slippery=False,
    render_mode="ansi"
)

actions = ["Left", "Down", "Right", "Up"]

state, info = env.reset(seed=42)
print(env.render())

for step in range(30):
    # Random action (no learning yet)
    action = env.action_space.sample()

    state, reward, terminated, truncated, info = env.step(action)

    print(f"Step {step + 1}: {actions[action]}")
    print(f"State: {state}, Reward: {reward}")
    print(env.render())

    time.sleep(0.4)

    if terminated or truncated:
        print("Episode finished!")
        time.sleep(1)

        state, info = env.reset()
        print(env.render())

env.close()
