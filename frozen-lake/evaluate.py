
import gymnasium as gym
import numpy as np
import time

def evaluate(mode="trained"):

    Q = np.load("q_table.npy")

    env = gym.make(
        "FrozenLake-v1",
        map_name="4x4",
        is_slippery=False,
        render_mode="ansi"
    )

    actions = ["Left", "Down", "Right", "Up"]

    turns = 100
    successes = 0

    while turns > 0:
        state, info = env.reset()
        done = False
        total_reward = 0

        while not done:
            # Choose the best learned action

            if mode == "trained":
                action = int(np.argmax(Q[state]))
            elif mode == "random":
                action = env.action_space.sample()  # Random action for testing

            state, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated
            total_reward += reward

            # print(f"Action: {actions[action]}")
            # print(f"State: {state}, Reward: {reward}")
            # print(env.render())

            # time.sleep(0.4)

        # print(f"Episode finished! Total reward: {total_reward}")

        if total_reward > 0:
            successes += 1

        turns -= 1

        # print(f"{mode} Successes: {successes}, Remaining turns: {turns}")

    
    env.close()

    print(f"Success rate({mode}): {successes / 100 * 100}%")



evaluate(mode="trained")
evaluate(mode="random")
