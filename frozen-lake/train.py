
import gymnasium as gym
import numpy as np

env = gym.make(
    "FrozenLake-v1",
    map_name="4x4",
    is_slippery=False
)

# 1. Initialise Q-table
Q = np.zeros((
    env.observation_space.n,
    env.action_space.n
))

# 2. Hyperparameters
alpha = 0.8        # Learning rate
gamma = 0.95       # Future reward discount
epsilon = 1.0      # Exploration probability
episodes = 20000

rng = np.random.default_rng(42)

# 3. Train
for episode in range(episodes):
    state, info = env.reset()
    done = False

    while not done:

        # Choose an action (epsilon-greedy)
        if rng.random() < epsilon:
            action = int(rng.integers(env.action_space.n))
        else:
            action = int(np.argmax(Q[state]))

        # Interact with the environment
        next_state, reward, terminated, truncated, info = (
            env.step(action)
        )

        done = terminated or truncated

        # Learn from the outcome
        old_value = Q[state, action]

        future_value = (
            0 if done else np.max(Q[next_state])
        )

        target = reward + gamma * future_value

        Q[state, action] = old_value + alpha * (
            target - old_value
        )

        state = next_state

    # Gradually reduce exploration
    epsilon = max(0.05, epsilon - 1 / episodes)

# 4. Save the learned Q-table
np.save("q_table.npy", Q)

print("Training complete!")
print(np.round(Q, 2))

env.close()
