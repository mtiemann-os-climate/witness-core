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

from pandas import DataFrame, concat
from sostrades_core.tools.post_processing.post_processing_factory import PostProcessingFactory

from sostrades_core.study_manager.study_manager import StudyManager
from climateeconomics.sos_processes.iam.witness_wo_energy.datacase_witness_wo_energy import \
    DataStudy as datacase_witness
from climateeconomics.sos_processes.iam.witness_wo_energy_dev.datacase_witness_wo_energy import \
    DataStudy as datacase_witness_dev
from climateeconomics.sos_processes.iam.witness_wo_energy_thesis.datacase_witness_wo_energy_solow import \
    DataStudy as datacase_witness_thesis
from energy_models.sos_processes.energy.MDA.energy_process_v0_mda.usecase import Study as datacase_energy

from sostrades_core.execution_engine.func_manager.func_manager import FunctionManager
from sostrades_core.execution_engine.func_manager.func_manager_disc import FunctionManagerDisc
from energy_models.core.energy_study_manager import DEFAULT_TECHNO_DICT
from climateeconomics.sos_processes.iam.witness.agriculture_mix_process.usecase import \
    AGRI_MIX_TECHNOLOGIES_LIST_FOR_OPT

from climateeconomics.core.tools.ClimateEconomicsStudyManager import ClimateEconomicsStudyManager
from energy_models.core.energy_process_builder import INVEST_DISCIPLINE_OPTIONS

import cProfile
from io import StringIO
import pstats

INEQ_CONSTRAINT = FunctionManagerDisc.INEQ_CONSTRAINT
AGGR_TYPE = FunctionManagerDisc.AGGR_TYPE
AGGR_TYPE_SUM = FunctionManager.AGGR_TYPE_SUM
AGGR_TYPE_SMAX = FunctionManager.AGGR_TYPE_SMAX


class Study(ClimateEconomicsStudyManager):

    def __init__(self, year_start=2020, year_end=2100, time_step=1, bspline=True, run_usecase=False,
                 execution_engine=None,
                 invest_discipline=INVEST_DISCIPLINE_OPTIONS[
                     2], techno_dict=DEFAULT_TECHNO_DICT, agri_techno_list=AGRI_MIX_TECHNOLOGIES_LIST_FOR_OPT,
                 process_level='val'):
        super().__init__(__file__, run_usecase=run_usecase, execution_engine=execution_engine)
        self.year_start = year_start
        self.year_end = year_end
        self.time_step = time_step
        self.bspline = bspline
        self.invest_discipline = invest_discipline
        self.techno_dict = techno_dict
        self.agri_techno_list = agri_techno_list
        self.process_level = process_level
        self.dc_energy = datacase_energy(
            self.year_start, self.year_end, self.time_step, bspline=self.bspline, execution_engine=execution_engine,
            invest_discipline=self.invest_discipline, techno_dict=techno_dict)
        self.sub_study_path_dict = self.dc_energy.sub_study_path_dict

    def setup_constraint_land_use(self):
        func_df = DataFrame(
            columns=['variable', 'parent', 'ftype', 'weight', AGGR_TYPE])
        list_var = []
        list_parent = []
        list_ftype = []
        list_weight = []
        list_aggr_type = []
        list_ns = []
        list_var.extend(
            ['land_demand_constraint'])
        list_parent.extend(['agriculture_constraint'])
        list_ftype.extend([INEQ_CONSTRAINT])
        list_weight.extend([-1.0])
        list_aggr_type.extend(
            [AGGR_TYPE_SUM])
        list_ns.extend(['ns_functions'])
        func_df['variable'] = list_var
        func_df['parent'] = list_parent
        func_df['ftype'] = list_ftype
        func_df['weight'] = list_weight
        func_df[AGGR_TYPE] = list_aggr_type
        func_df['namespace'] = list_ns

        return func_df

    def setup_usecase(self):
        setup_data_list = []

        # -- load data from energy pyworld3
        # -- Start with energy to have it at first position in the list...

        self.dc_energy.study_name = self.study_name
        self.energy_mda_usecase = self.dc_energy
        # -- load data from witness
        if self.process_level == 'val':
            dc_witness = datacase_witness(
                self.year_start, self.year_end, self.time_step)

        elif self.process_level == 'thesis':
            dc_witness = datacase_witness_thesis(
                self.year_start, self.year_end, self.time_step)

        else:
            dc_witness = datacase_witness_dev(
                self.year_start, self.year_end, self.time_step, agri_techno_list=self.agri_techno_list)

        dc_witness.study_name = self.study_name
        witness_input_list = dc_witness.setup_usecase()
        setup_data_list = setup_data_list + witness_input_list

        energy_input_list = self.dc_energy.setup_usecase()
        setup_data_list = setup_data_list + energy_input_list

        dspace_energy = self.dc_energy.dspace

        self.merge_design_spaces([dspace_energy, dc_witness.dspace])

        # constraint land use
        land_use_df_constraint = self.setup_constraint_land_use()

        # WITNESS
        # setup objectives
        self.func_df = concat(
            [dc_witness.setup_objectives(), dc_witness.setup_constraints(), self.dc_energy.setup_constraints(),
             self.dc_energy.setup_objectives(), land_use_df_constraint])

        self.energy_list = self.dc_energy.energy_list
        self.ccs_list = self.dc_energy.ccs_list
        self.dict_technos = self.dc_energy.dict_technos

        numerical_values_dict = {
            f'{self.study_name}.epsilon0': 1.0,
            f'{self.study_name}.max_mda_iter': 50,
            f'{self.study_name}.tolerance': 1.0e-10,
            f'{self.study_name}.n_processes': 1,
            f'{self.study_name}.linearization_mode': 'adjoint',
            f'{self.study_name}.sub_mda_class': 'GSPureNewtonMDA',
            f'{self.study_name}.cache_type': 'SimpleCache', }
        # f'{self.study_name}.gauss_seidel_execution': True}

        setup_data_list.append(numerical_values_dict)

        return setup_data_list

    def run(self, logger_level=None,
            dump_study=False,
            for_test=False):

        profil = cProfile.Profile()
        profil.enable()
        ClimateEconomicsStudyManager.run(
            self, logger_level=logger_level, dump_study=dump_study, for_test=for_test)
        profil.disable()

        result = StringIO()

        ps = pstats.Stats(profil, stream=result)
        ps.sort_stats('cumulative')
        ps.print_stats(500)
        result = result.getvalue()
        print(result)


if '__main__' == __name__:
    uc_cls = Study(run_usecase=True)
    uc_cls.load_data()

    # print(len(uc_cls.execution_engine.root_process.proxy_disciplines))
    #  self.exec_eng.dm.export_couplings(
    #     in_csv=True, f_name='couplings.csv')

    # uc_cls.execution_engine.root_process.coupling_structure.graph.export_initial_graph(
    #     "initial.pdf")
    #     uc_cls.execution_engine.root_process.coupling_structure.graph.export_reduced_graph(
    #         "reduced.pdf")

    # DEBUG MIN MAX COUPLINGS
    #     uc_cls.execution_engine.set_debug_mode(mode='min_max_couplings')
    #     pd.set_option('display.max_rows', None)
    #     pd.set_option('display.max_columns', None)
    # #     pd.set_option('display.width', None)
    #     profil = cProfile.Profile()
    #     profil.enable()

    uc_cls.run()
#     profil.disable()
#
#     result = StringIO()
#
#     ps = pstats.Stats(profil, stream=result)
#     ps.sort_stats('cumulative')
#     ps.print_stats(500)
#     result = result.getvalue()
#     print(result)

# ppf = PostProcessingFactory()
# all_post_processings = ppf.get_all_post_processings(
#     execution_engine=uc_cls.execution_engine, filters_only=False,
#     as_json=False, for_test=False)

# for graph in graph_list:
#     graph.to_plotly().show()

#     if disc.sos_name == 'EnergyMix.electricity.Nuclear':
#         filters = ppf.get_post_processing_filters_by_discipline(
#             disc)
#         graph_list = ppf.get_post_processing_by_discipline(
#             disc, filters, as_json=False)

#         for graph in graph_list:
#             graph.to_plotly().show()

#     if disc.sos_name == 'EnergyMix.electricity.WindOnshore':
#         filters = ppf.get_post_processing_filters_by_discipline(
#             disc)
#         graph_list = ppf.get_post_processing_by_discipline(
#             disc, filters, as_json=False)

#         for graph in graph_list:
#             graph.to_plotly().show()

#     if disc.sos_name == 'EnergyMix.electricity':
#         filters = ppf.get_post_processing_filters_by_discipline(
#             disc)
#         graph_list = ppf.get_post_processing_by_discipline(
#             disc, filters, as_json=False)

#         for graph in graph_list:
#             graph.to_plotly().show()
