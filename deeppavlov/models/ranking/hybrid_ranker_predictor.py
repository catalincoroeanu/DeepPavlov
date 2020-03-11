# Copyright 2019 Neural Networks and Deep Learning lab, MIPT
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from logging import getLogger
import numpy as np

from deeppavlov.core.common.registry import register
from deeppavlov.core.models.estimator import Component

logger = getLogger(__name__)


@register("hybrid_ranker_predictor")
class HybridRankerPredictor(Component):
    def __init__(
        self,
        sample_size: int = 14,
        lambda_coeff: float = 10.0,
        return_topn: bool = False,
        topn: int = 10,
        ext_score_trashhold: float = 0.0,
        **kwargs,
    ):
        self.sample_size = sample_size
        self.lambda_coeff = lambda_coeff
        self.return_topn = return_topn
        self.topn = topn
        self.ext_score_trashhold = ext_score_trashhold

    def __call__(self, candidates_batch, preds_batch, ext_score_batch=[]):
        """
        return list of best responses and its confidences
        """

        responses_batch = []
        responses_preds = []
        ext_score_flag = all(
            [
                cand_dim != ext_feat_dim
                for cand_dim, ext_feat_dim in zip(np.array(candidates_batch), np.array(ext_score_batch))
            ]
        )
        logger.error(f"ext_score_flag: {ext_score_flag}")

        for i in range(len(candidates_batch)):
            cand2pred = {candidates_batch[i][j]: preds_batch[i][j] for j in range(len(candidates_batch[i]))}

            if ext_score_flag:
                logger.error(f"candidates_batch[i]: {[ f'{i}: {n}'for i, n in enumerate(candidates_batch[i])]}")
                logger.error(f"ext_score_batch[i]: {[ f'{i}: {n}'for i, n in enumerate(ext_score_batch[i])]}")
                candidates_list = [
                    cand
                    for cand, ext_score in zip(candidates_batch[i], ext_score_batch[i])
                    if ext_score > self.ext_score_trashhold
                ]
                logger.error(f"candidates_list: {[ f'{i}: {n}'for i, n in enumerate(candidates_list)]}")
                candidates_list = list(set(candidates_list))
            else:
                candidates_list = list(set(candidates_batch[i]))

            scores = np.array([cand2pred[c] for c in candidates_list])

            sorted_ids = np.flip(np.argsort(scores), -1)
            # chosen_index = np.random.choice(sorted_ids[:self.sample_size])  # choose a random answer as the best one

            # debug
            # sorted_scores = [scores[i] for i in sorted_ids]  # [0.9, 0.6, 0.55, 0.54, 0.4, 0.33, 0.32, 0.3]
            # filtered_score_ids = np.where(np.array(sorted_scores) >= 0.5)  # array([0, 1, 2, 3]),)

            if not self.return_topn:
                i = np.arange(self.sample_size)
                w = np.exp(-i / self.lambda_coeff)
                w = w / w.sum()
                # print("distribution:", w)  # DEBUG

                chosen_index = np.random.choice(sorted_ids[: self.sample_size], p=w)

                # logger.debug('candidates: ' + str([candidates_list[i] for i in sorted_ids[:self.sample_size]]) + 'scores: ' +
                #              str([sorted_scores[i] for i in range(self.sample_size)]))  # DEBUG
                # logger.debug('answer: ' + str(chosen_index) + " ; " + str(scores[chosen_index]) + " ; " +
                #              str(candidates_list[chosen_index]))  # DEBUG

                responses_batch.append(candidates_list[chosen_index])
                responses_preds.append(scores[chosen_index])
            else:
                responses_batch.append(np.array(candidates_list)[sorted_ids[: self.topn]])
                responses_preds.append(scores[sorted_ids[: self.topn]])
                # logger.debug('sorted scores: ' + str(scores[sorted_ids[:self.topn]]))

        return responses_batch, responses_preds
