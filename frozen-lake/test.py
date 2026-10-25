
import gymnasium as gym
import numpy as np
import time

Q = np.load("q_table.npy")

env = gym.make(
    "FrozenLake-v1",
    map_name="4x4",
    is_slippery=False,
    render_mode="ansi"
)

actions = ["Left", "Down", "Right", "Up"]

state, info = env.reset()
done = False
total_reward = 0

print(env.render())

while not done:
    # Choose the best learned action
    # action = int(np.argmax(Q[state]))
    action = env.action_space.sample()  # Random action for testing

    state, reward, terminated, truncated, info = env.step(action)
    done = terminated or truncated
    total_reward += reward

    print(f"Action: {actions[action]}")
    print(f"State: {state}, Reward: {reward}")
    print(env.render())

    time.sleep(0.4)

print(f"Episode finished! Total reward: {total_reward}")

env.close()
