import pandas as pd

from climateeconomics.glossarycore import GlossaryCore


class SectorRedistributionEnergyModel:
    """model for energy and investment redistribution between economy sectors"""
    def __init__(self):
        self.inputs = dict()
        self.sectors = list()
        self.deduced_sector = ''
        self.missing_sector_share = None

    def compute_energy_redistribution(self) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
        """
        Distribute total energy production between sectors using sector list and share per sector input
        In addition to sectors list energy is distributed for residential and "other" category
        """
        total_energy_production: pd.DataFrame = self.inputs[GlossaryCore.EnergyProductionValue]
        total_energy_production_values = total_energy_production[GlossaryCore.TotalProductionValue].values
        all_sectors_energy_df = {GlossaryCore.Years: total_energy_production[GlossaryCore.Years]}
        sectors_energy = {}
        computed_sectors = list(filter(lambda x: x != self.deduced_sector, self.sectors))
        for sector in computed_sectors:
            sector_energy_values = self.inputs[f'{sector}.{GlossaryCore.ShareSectorEnergyDfValue}'][
                                           GlossaryCore.ShareSectorEnergy].values / 100. * total_energy_production_values
            sector_energy_df = pd.DataFrame(
                {GlossaryCore.Years: total_energy_production[GlossaryCore.Years].values,
                 GlossaryCore.TotalProductionValue: sector_energy_values}
            )
            sectors_energy[sector] = sector_energy_df
            all_sectors_energy_df[sector] = sector_energy_values

        #Residential energy
        residential_energy_values = self.inputs[GlossaryCore.ShareResidentialEnergyDfValue][
                                                GlossaryCore.ShareSectorEnergy].values/100 * total_energy_production_values

        residential_energy_df = pd.DataFrame(
                {GlossaryCore.Years: total_energy_production[GlossaryCore.Years].values,
                 GlossaryCore.TotalProductionValue: residential_energy_values}
            )
        all_sectors_energy_df[GlossaryCore.ResidentialCategory] = residential_energy_values

        #Other category
        other_energy_values = self.inputs[GlossaryCore.ShareOtherEnergyDfValue][
                                                GlossaryCore.ShareSectorEnergy].values/100 * total_energy_production_values
        all_sectors_energy_df[GlossaryCore.OtherEnergyCategory] = other_energy_values

        all_sectors_energy_df = pd.DataFrame(all_sectors_energy_df)

        #Compute leftover energy for last sector
        missing_sector_energy = total_energy_production_values -\
                                all_sectors_energy_df.loc[:,all_sectors_energy_df.columns != GlossaryCore.Years].sum(axis=1).values

        all_sectors_energy_df[self.deduced_sector] = missing_sector_energy
        sectors_energy[self.deduced_sector] = pd.DataFrame(
                {GlossaryCore.Years: total_energy_production[GlossaryCore.Years].values,
                 GlossaryCore.TotalProductionValue: missing_sector_energy}
            )

        return sectors_energy, all_sectors_energy_df, residential_energy_df

    def compute(self, inputs: dict):
        self.inputs = inputs
        self.sectors = inputs[GlossaryCore.SectorListValue]
        self.deduced_sector = inputs[GlossaryCore.MissingSectorNameValue]

        sectors_energy, all_sectors_energy_df, residential_energy_df = self.compute_energy_redistribution()

        return sectors_energy, all_sectors_energy_df, residential_energy_df
