# -*- coding: utf-8 -*-
"""Federated Learning basic

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1FIr1QQjnmVegYIPltvt9xayMysLpxDdE

https://ai.googleblog.com/2017/04/federated-learning-collaborative.html

https://blog.openmined.org/upgrade-to-federated-learning-in-10-lines/
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torchvision import datasets, transforms

!pip install syft

"""And we also add those specific to PySyft. In particular we define the remote workers alice and bob, which will hold the remote data while a local worker (or client) will orchestrate the learning task, as shown on the schema in Figure 1. Note that we use virtual workers: these workers behave exactly like normal remote workers except that they live in the same Python program. Hence, we still serialize the commands to be exchanged between the workers but we don't really send them over the network. This way, we avoid all network issues and can focus on the core logic of the project."""

import syft as sy
# hook PyTorch ie add extra functionalities to support Federated Learning
hook = sy.TorchHook(torch)
#NEW: define remote worker bob
bob = sy.VirtualWorker(hook, id="bob")
alice = sy.VirtualWorker(hook, id="alice")

class Arguments():
    def __init__(self):
        self.batch_size = 64
        self.test_batch_size = 1000
        self.epochs = 10
        self.lr = 0.01
        self.momentum = 0.5
        self.no_cuda = False
        self.seed = 1
        self.log_interval = 10
        self.save_model = False

args = Arguments()

# device
cuda = not args.no_cuda and torch.cuda.is_available()
device = torch.device("cuda" if cuda else "cpu")
# seed
torch.manual_seed(args.seed)
# for data load for workes
kwargs = {'num_workers': 1, 'pin_memory': True} if use_cuda else {}

"""We first load the data and transform the training Dataset into a Federated Dataset using the .federate method: it splits the dataset in two parts and send them to the workers alice and bob. This federated dataset is now given to a Federated DataLoader which will iterate over remote batches.

# **IMPORTANT**
"""

# key FederatedDataLoader 
federated_train_loader = sy.FederatedDataLoader(
    datasets.MNIST('../data', train=True, download=True,
                   transform=transforms.Compose([
                   transforms.ToTensor(),
                   transforms.Normalize((0.1307,), (0.3081,))
                   ]))
# we distribute the dataset across all the workers, it's now a FederatedDataset
.federate((bob, alice)), batch_size=args.batch_size, shuffle=True, **kwargs)
# and standart data loader
test_loader = torch.utils.data.DataLoader(
    datasets.MNIST('../data', train=False, transform=transforms.Compose([
                       transforms.ToTensor(),
                       transforms.Normalize((0.1307,), (0.3081,))
                   ])),
    batch_size=args.test_batch_size, shuffle=True, **kwargs)

# jast normal nn
class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()
        self.conv1 = nn.Conv2d(1, 20, 5, 1)
        self.conv2 = nn.Conv2d(20, 50, 5, 1)
        self.fc1 = nn.Linear(4*4*50, 500)
        self.fc2 = nn.Linear(500, 10)

    def forward(self, x):
        x = F.relu(self.conv1(x))
        x = F.max_pool2d(x, 2, 2)
        x = F.relu(self.conv2(x))
        x = F.max_pool2d(x, 2, 2)
        x = x.view(-1, 4*4*50)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return F.log_softmax(x, dim=1)

"""For the train function, because the data batches are distributed across alice and bob, you need to send the model to the right location for each batch using model.send(...). Then, you perform all the operations remotely with the same syntax like you're doing local PyTorch. When you're done, you get back the model updated and the loss to look for improvement using the .get() method."""

def train(args, model, device, train_loader, optimizer, epoch):
    model.train()
    for batch_idx, (data, target) in enumerate(federated_train_loader):
        # send the model to the right location
        model.send(data.location) 
        data, target = data.to(device), target.to(device)
        optimizer.zero_grad()
        output = model(data)
        loss = F.nll_loss(output, target)
        loss.backward()
        optimizer.step()
        # get the model back
        model.get()
        if batch_idx % args.log_interval == 0:
            #get the loss back
            loss = loss.get() 
            print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                epoch, batch_idx * args.batch_size, len(train_loader) * args.batch_size, #batch_idx * len(data), len(train_loader.dataset),
                100. * batch_idx / len(train_loader), loss.item()))

# test on local machine
def test(args, model, device, test_loader):
    model.eval()
    test_loss = 0
    correct = 0
    with torch.no_grad():
        for data, target in test_loader:
            data, target = data.to(device), target.to(device)
            output = model(data)
            test_loss += F.nll_loss(output, target, reduction='sum').item() 
            pred = output.argmax(1, keepdim=True) 

    test_loss /= len(test_loader.dataset)

    print('\nTest set: Average loss: {:.4f}, Accuracy: {}/{} ({:.0f}%)\n'.format(
        test_loss, correct, len(test_loader.dataset),
        100. * correct / len(test_loader.dataset)))

"""The training is now done as usual."""

model = Net().to(device)
optimizer = optim.SGD(model.parameters(), lr=args.lr) # TODO momentum is not supported at the moment

for epoch in range(1, args.epochs + 1):
    train(args, model, device, federated_train_loader, optimizer, epoch)
    test(args, model, device, test_loader)

if (args.save_model):
    torch.save(model.state_dict(), "mnist_cnn.pt")

"""As you observe, we only had to modify 10 lines of code to upgrade the official Pytorch example on MNIST to a real Federated Learning task!

Of course, there are dozen of improvements we could think of. We would like the computation to operate in parallel on the workers and perform federated averaging, to update the central model every n batches only, to reduce the number of messages we use to communicate between workers while orchestrating the training, etc. These are features we're working on to make Federated Learning ready for a production environment and we'll write about them as soon as they are released!

You should now be able to do Federated Learning by yourself! If you enjoyed this and would like to join the movement toward privacy preserving, decentralized ownership of AI and the AI supply chain (data), you can do so in the following ways!
"""

