'''
Copyright 2022 Airbus SAS

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
'''
'''
mode: python; py-indent-offset: 4; tab-width: 8; coding: utf-8
'''
import unittest
from os.path import join, dirname
from pandas import read_csv
from climateeconomics.core.core_resources.resources_model import ResourceModel
from sos_trades_core.execution_engine.execution_engine import ExecutionEngine
from sos_trades_core.tests.core.abstract_jacobian_unit_test import AbstractJacobianUnittest


class GasResourceJacobianDiscTest(AbstractJacobianUnittest):
    """
    Gas resource jacobian test class
    """
    # AbstractJacobianUnittest.DUMP_JACOBIAN = True

    def analytic_grad_entry(self):
        return [
            self.test_gas_resource_analytic_grad,
            self.test_gas_resource_demand_variable_analytic_grad
        ]

    def setUp(self):
        '''
        Initialize third data needed for testing
        '''
        self.year_start = 2020
        self.year_end = 2100

        data_dir = join(dirname(__file__), 'data')

        self.energy_gas_demand_df = read_csv(
            join(data_dir, 'all_demand_from_energy_mix.csv'), usecols=['years','natural_gas_resource'])
        self.energy_gas_variable_demand_df = read_csv(
            join(data_dir, 'all_demand_variable.csv'), usecols=['years','natural_gas_resource'])
        # part to adapt lenght to the year range

        self.energy_gas_demand_df = self.energy_gas_demand_df.loc[self.energy_gas_demand_df['years']
                                                                  >= self.year_start]
        self.energy_gas_demand_df = self.energy_gas_demand_df.loc[self.energy_gas_demand_df['years']
                                                                  <= self.year_end]
        self.energy_gas_variable_demand_df = self.energy_gas_variable_demand_df.loc[self.energy_gas_variable_demand_df['years']
                                                                    >= self.year_start]
        self.energy_gas_variable_demand_df = self.energy_gas_variable_demand_df.loc[self.energy_gas_variable_demand_df['years']
                                                                  <= self.year_end]
    def test_gas_resource_analytic_grad(self):

        self.name = 'Test'
        self.ee = ExecutionEngine(self.name)
        self.model_name = 'gas_resource'

        ns_dict = {'ns_public': f'{self.name}',
                   'ns_witness': f'{self.name}.{self.model_name}',
                   'ns_functions': f'{self.name}.{self.model_name}',
                   'natural_gas_resource': f'{self.name}.{self.model_name}',
                   'ns_resource': f'{self.name}.{self.model_name}'}

        self.ee.ns_manager.add_ns_def(ns_dict)

        mod_path = 'climateeconomics.sos_wrapping.sos_wrapping_resources.sos_wrapping_gas_resource.gas_resource_model.gas_resource_disc.GasDiscipline'
        builder = self.ee.factory.get_builder_from_module(
            self.model_name, mod_path)

        self.ee.factory.set_builders_to_coupling_builder(builder)

        self.ee.configure()
        self.ee.display_treeview_nodes()

        inputs_dict = {f'{self.name}.year_start': self.year_start,
                       f'{self.name}.year_end': self.year_end,
                       f'{self.name}.{self.model_name}.{ResourceModel.DEMAND}': self.energy_gas_demand_df
                       }
        self.ee.load_study_from_input_dict(inputs_dict)
        disc_techno = self.ee.root_process.sos_disciplines[0]

        self.check_jacobian(location=dirname(__file__), filename=f'jacobian_gas_discipline.pkl',
                            discipline=disc_techno, step=1e-15, derr_approx='complex_step',
                            inputs=[
                                f'{self.name}.{self.model_name}.{ResourceModel.DEMAND}'],
                            outputs=[f'{self.name}.{self.model_name}.{ResourceModel.RESOURCE_STOCK}',
                                     f'{self.name}.{self.model_name}.{ResourceModel.RESOURCE_PRICE}',
                                     f'{self.name}.{self.model_name}.{ResourceModel.USE_STOCK}',
                                     f'{self.name}.{self.model_name}.{ResourceModel.PRODUCTION}'])

    def test_gas_resource_demand_variable_analytic_grad(self):
        
        self.name = 'Test'
        self.ee = ExecutionEngine(self.name)
        self.model_name = 'gas_resource'

        ns_dict = {'ns_public': f'{self.name}',
                   'ns_witness': f'{self.name}.{self.model_name}',
                   'ns_functions': f'{self.name}.{self.model_name}',
                   'natural_gas_resource':f'{self.name}.{self.model_name}',
                   'ns_resource': f'{self.name}.{self.model_name}'}

        self.ee.ns_manager.add_ns_def(ns_dict)

        mod_path = 'climateeconomics.sos_wrapping.sos_wrapping_resources.sos_wrapping_gas_resource.gas_resource_model.gas_resource_disc.GasDiscipline'
        builder = self.ee.factory.get_builder_from_module(self.model_name, mod_path)

        self.ee.factory.set_builders_to_coupling_builder(builder)

        self.ee.configure()
        self.ee.display_treeview_nodes()

        inputs_dict = {f'{self.name}.year_start': self.year_start,
                       f'{self.name}.year_end': self.year_end,
                       f'{self.name}.{self.model_name}.{ResourceModel.DEMAND}': self.energy_gas_variable_demand_df
                       }
        self.ee.load_study_from_input_dict(inputs_dict)
        disc_techno = self.ee.root_process.sos_disciplines[0]     
        
        self.check_jacobian(location=dirname(__file__), filename=f'jacobian_gas_demand_variable_discipline.pkl', 
                            discipline=disc_techno, step=1e-15, derr_approx='complex_step', 
                            inputs=[f'{self.name}.{self.model_name}.{ResourceModel.DEMAND}'],
                            outputs=[f'{self.name}.{self.model_name}.{ResourceModel.RESOURCE_STOCK}',
                                     f'{self.name}.{self.model_name}.{ResourceModel.RESOURCE_PRICE}',
                                     f'{self.name}.{self.model_name}.{ResourceModel.USE_STOCK}',
                                     f'{self.name}.{self.model_name}.{ResourceModel.PRODUCTION}'])
