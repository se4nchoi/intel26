import matplotlib.pyplot as plt
from sklearn import linear_model

reg = linear_model.LinearRegression()

X = [[174], [152], [138], [128], [186]]
y = [71, 55, 46, 38, 80]

reg.fit(X, y)
print(reg.predict([[180]]))

plt.scatter(X, y, color='blue')
plt.plot(X, reg.predict(X), color='red', linewidth=4)
plt.xticks(())
plt.yticks(())

# plt.show() # This tries to open an interactive window and causes a warning in non-GUI environments.

# A better approach for scripts: save the figure to a file.
import os

output_folder = 'plots'
curr_folder = os.path.dirname(__file__)
output_folder = os.path.join(curr_folder, output_folder)

if not os.path.exists(output_folder):
    os.makedirs(output_folder)

plot_number = 1 # You can increment this for multiple plots
output_filepath = os.path.join(output_folder, f'regression_plot_{plot_number}.png')
plt.savefig(output_filepath)
print(f"\nPlot saved to {output_filepath}")
