This model gathers production, price and stock ressource data coming from resource disciplines and aggregates the result in a global dataframe. It also takes in input the resource demand from the energy mix.
In output we have some dataframe that link the different resource dataframe of production, stock and price. The model also computes the ratio of the available resource stock on the demand and the ratio of the maximum production per year on the demand. These dataframe help us to vizualise when we will lack the resources.
The model also adds the non-model resource price and convert the different unit of data to get all the result in the same unit. 