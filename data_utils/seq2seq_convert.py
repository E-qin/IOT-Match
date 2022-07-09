import sys
sys.path.append("..")
from models.selector_two_multi_class_ot_v3 import Selector2_mul_class, args, load_checkpoint, OT, load_data, data_extract_npy, data_extract_json, device
import torch
from utils.snippets import *
import torch
import json
"""
todo 需要添加一个分类器，对相似句子与不相似句子进行分类
"""
def model_class(model, OT_model, case_A, case_B, seq_len_A, seq_len_B):
    """

    :param model:
    :param OT_model:
    :param case_A:
    :param case_B:
    :return: AO, YO, ZO, AI, YI, ZI
    """
    AO_a, YO_a, ZO_a, AI_a, YI_a, ZI_a = [], [], [], [], [], []
    AO_b, YO_b, ZO_b, AI_b, YI_b, ZI_b = [], [], [], [], [], []

    output_batch_A, batch_mask_A = model(case_A)
    output_batch_B, batch_mask_B = model(case_B)
    plan_list = OT_model(output_batch_A, output_batch_B, case_A, case_B, None,
                            batch_mask_A, batch_mask_B, 'valid')
    OT_matrix = torch.ge(plan_list, 1 / case_A.shape[1] / args.threshold_ot).long()
    vec_correct_A = torch.argmax(output_batch_A, dim=-1).long()[0][:seq_len_A]
    vec_correct_B = torch.argmax(output_batch_B, dim=-1).long()[0][:seq_len_B]
    relation_A = torch.sum(OT_matrix[0], dim=1)
    relation_B = torch.sum(OT_matrix[0], dim=0)

    for i, label in enumerate(vec_correct_A):
        if label == 1:
            if relation_A[i] >= 1:
                AI_a.append(i)
            else:
                AO_a.append(i)
        elif label == 2:
            if relation_A[i] >= 1:
                YI_a.append(i)
            else:
                YO_a.append(i)
        elif label == 3:
            if relation_A[i] >= 1:
                ZI_a.append(i)
            else:
                ZO_a.append(i)

    for i, label in enumerate(vec_correct_B):
        if label == 1:
            if relation_B[i] >= 1:
                AI_b.append(i)
            else:
                AO_b.append(i)
        elif label == 2:
            if relation_B[i] >= 1:
                YI_b.append(i)
            else:
                YO_b.append(i)
        elif label == 3:
            if relation_B[i] >= 1:
                ZI_b.append(i)
            else:
                ZO_b.append(i)
    AO, YO, ZO, AI, YI, ZI = [AO_a, AO_b], [YO_a, YO_b], [ZO_a, ZO_b], [AI_a, AI_b], [YI_a, YI_b], [ZI_a, ZI_b]

    return AO, YO, ZO, AI, YI, ZI, [vec_correct_A+(torch.ge(relation_A[:seq_len_A], 1)*3)*vec_correct_A, vec_correct_B+(torch.ge(relation_B[:seq_len_B], 1)*3)*vec_correct_B]




def generate_text_cluster(case_a, case_b, d, AO, YO, ZO, AI, YI, ZI, A_all_true, Y_all_true, Z_all_true, AI_true, YI_true, ZI_true):
    source_1_a = ''.join(["[AO]" + case_a[0][i] for i in AO[0]] + ["[YO]" + case_a[0][i] for i in YO[0]] +
                         ["[ZO]" + case_a[0][i] for i in ZO[0]] + ["[AI]" + case_a[0][i] for i in AI[0]] +
                         ["[YI]" + case_a[0][i] for i in YI[0]] + ["[ZI]" + case_a[0][i] for i in ZI[0]])

    source_1_b = ''.join(["[AO]" + case_b[0][i] for i in AO[1]] + ["[YO]" + case_b[0][i] for i in YO[1]] +
                         ["[ZO]" + case_b[0][i] for i in ZO[1]] + ["[AI]" + case_b[0][i] for i in AI[1]] +
                         ["[YI]" + case_b[0][i] for i in YI[1]] + ["[ZI]" + case_b[0][i] for i in ZI[1]])

    source_2_a = ''.join(
        ["[AO]" + case_a[0][i] for i in A_all_true[0] if i not in AI_true[0]] + ["[YO]" + case_a[0][i] for i in
                                                                                 Y_all_true[0] if i not in YI_true[0]] +
        ["[ZO]" + case_a[0][i] for i in Z_all_true[0] if i not in ZI_true[0]] + ["[AI]" + case_a[0][i] for i in
                                                                                 AI_true[0]] +
        ["[YI]" + case_a[0][i] for i in YI_true[0]] + ["[ZI]" + case_a[0][i] for i in ZI_true[0]])

    source_2_b = ''.join(
        ["[AO]" + case_b[0][i] for i in A_all_true[1] if i not in AI_true[1]] + ["[YO]" + case_b[0][i] for i in
                                                                                 Y_all_true[1] if i not in YI_true[1]] +
        ["[ZO]" + case_b[0][i] for i in Z_all_true[1] if i not in ZI_true[1]] + ["[AI]" + case_b[0][i] for i in
                                                                                 AI_true[1]] +
        ["[YI]" + case_b[0][i] for i in YI_true[1]] + ["[ZI]" + case_b[0][i] for i in ZI_true[1]])

    result = {
        'source_1': source_1_a + source_1_b,
        'source_2': source_2_a + source_2_b,
        'explanation': '；'.join(list(d['explanation'].values())),
        'source_1_dis': [source_1_a, source_1_b],
        'source_2_dis': [source_2_a, source_2_b],
        'label': d['label']
    }
    return result


def get_extract_text(case_a, prediction):
    source_1_a = ''
    for i, output_class in enumerate(prediction):
        if output_class == 1:
            source_1_a += "[AO]" + case_a[0][i]
        elif output_class == 2:
            source_1_a += "[YO]" + case_a[0][i]
        elif output_class == 3:
            source_1_a += "[ZO]" + case_a[0][i]
        elif output_class == 4:
            source_1_a += "[AI]" + case_a[0][i]
        elif output_class == 5:
            source_1_a += "[YI]" + case_a[0][i]
        elif output_class == 6:
            source_1_a += "[ZI]" + case_a[0][i]
        else:
            pass
    return source_1_a


def get_extract_text_wo_token(case_a, prediction):
    source_1_a = ''
    for i, output_class in enumerate(prediction):
        if output_class != 0:
            source_1_a += case_a[0][i]
        else:
            pass
    return source_1_a


def generate_text_sort(case_a, case_b, d, prediction, label):

    source_1_a = get_extract_text(case_a, prediction[0])
    source_1_b = get_extract_text(case_b, prediction[1])
    source_2_a = get_extract_text(case_a, label[0])
    source_2_b = get_extract_text(case_b, label[1])

    result = {
        'source_1': source_1_a + source_1_b,
        'source_2': source_2_a + source_2_b,
        'explanation': '；'.join(list(d['explanation'].values())),
        'source_1_dis': [source_1_a, source_1_b],
        'source_2_dis': [source_2_a, source_2_b],
        'label': d['label']
    }
    return result


def generate_text_wo_token(case_a, case_b, d, prediction, label):

    source_1_a = get_extract_text_wo_token(case_a, prediction[0])
    source_1_b = get_extract_text_wo_token(case_b, prediction[1])
    source_2_a = get_extract_text_wo_token(case_a, label[0])
    source_2_b = get_extract_text_wo_token(case_b, label[1])

    result = {
        'source_1': source_1_a + source_1_b,
        'source_2': source_2_a + source_2_b,
        'explanation': '；'.join(list(d['explanation'].values())),
        'source_1_dis': [source_1_a, source_1_b],
        'source_2_dis': [source_2_a, source_2_b],
        'label': d['label']
    }
    return result


def fold_convert_our_data_ot(data, data_x, type, generate=False, generate_mode = 'cluster'):
    """每一fold用对应的模型做数据转换
    """

    with torch.no_grad():
        model = Selector2_mul_class(args.input_size, args.hidden_size, kernel_size=args.kernel_size, dilation_rate=[1, 2, 4, 8, 1, 1])
        load_checkpoint(model, None, 2, "/new_disk2/zhongxiang_sun/code/explanation_project/explanation_model/models/weights/extract/extract-criterion-BCEFocal-onehot-1-ot_mode-max-convert_to_onehot-1-weight-100-simot-1-simpercent-1.0.pkl")
        model = model.to(device)
        ot_model = OT()
        ot_model = ot_model.to(device)
        load_checkpoint(ot_model, None, 2, "/new_disk2/zhongxiang_sun/code/explanation_project/explanation_model/models/weights/extract/extract_ot-criterion-BCEFocal-onehot-1-ot_mode-max-convert_to_onehot-1-weight-100-simot-1-simpercent-1.0.pkl")
        results = []
        print(type+"ing")
        for i, d in enumerate(data):
            if type == 'match' and d["label"] == 2 or type == 'midmatch' and d["label"] == 1 or type == 'dismatch' and d["label"] == 0:
                case_a = d['case_A']
                case_b = d['case_B']
                important_A, important_B = [], []
                data_y_seven_class_A, data_y_seven_class_B = [0]*len(case_a[0]), [0]*len(case_b[0])
                for pos_list in d['relation_label'].values():
                    for pos in pos_list:
                        row, col = pos[0], pos[-1]
                        important_A.append(row)
                        important_B.append(col)

                for j in case_a[1]:
                    if j[0] in important_A:
                        data_y_seven_class_A[j[0]] = j[1] + 3
                    else:
                        data_y_seven_class_A[j[0]] = j[1]

                for j in case_b[1]:
                    if j[0] in important_B:
                        data_y_seven_class_B[j[0]] = j[1] + 3
                    else:
                        data_y_seven_class_B[j[0]] = j[1]
                label = [data_y_seven_class_A, data_y_seven_class_B]



                AO, YO, ZO, AI, YI, ZI, prediction = model_class(model, ot_model, torch.tensor(np.expand_dims(data_x[2*i], axis=0), device=device),
                                                     torch.tensor(np.expand_dims(data_x[2*i+1], axis=0), device=device),len(case_a[0]), len(case_b[0]))

                A_all_true, Y_all_true, Z_all_true, AI_true, YI_true, ZI_true = [], [], [], [], [], []

                temp_a, temp_b = [], []
                for i in d['relation_label']['relation_label_aqss']:
                    temp_a.append(i[0])
                    temp_b.append(i[1])
                AI_true.append(temp_a)
                AI_true.append(temp_b)

                temp_a, temp_b = [], []
                for i in d['relation_label']['relation_label_yjss']:
                    temp_a.append(i[0])
                    temp_b.append(i[1])
                YI_true.append(temp_a)
                YI_true.append(temp_b)

                temp_a, temp_b = [], []
                for i in d['relation_label']['relation_label_zyjd']:
                    temp_a.append(i[0])
                    temp_b.append(i[1])
                ZI_true.append(temp_a)
                ZI_true.append(temp_b)
                aqss_temp, yjss_temp, zyjd_temp = [], [], []
                for i in case_a[1]:
                    if i[1] == 1:
                        aqss_temp.append(i[0])
                    elif i[1] == 2:
                        yjss_temp.append(i[0])
                    elif i[1] == 3:
                        zyjd_temp.append(i[0])
                A_all_true.append(aqss_temp)
                Y_all_true.append(yjss_temp)
                Z_all_true.append(zyjd_temp)

                aqss_temp, yjss_temp, zyjd_temp = [], [], []
                for i in case_b[1]:
                    if i[1] == 1:
                        aqss_temp.append(i[0])
                    elif i[1] == 2:
                        yjss_temp.append(i[0])
                    elif i[1] == 3:
                        zyjd_temp.append(i[0])
                A_all_true.append(aqss_temp)
                Y_all_true.append(yjss_temp)
                Z_all_true.append(zyjd_temp)
                if generate:
                    if generate_mode == 'cluster':
                        results.append(generate_text_cluster(case_a, case_b, d, AO, YO, ZO, AI, YI, ZI, A_all_true, Y_all_true, Z_all_true, AI_true, YI_true,
                                      ZI_true))
                    elif generate_mode == 'sort':
                        results.append(generate_text_sort(case_a, case_b, d, prediction, label))
                    else:
                        results.append(generate_text_wo_token(case_a, case_b, d, prediction, label))

        if generate:
            return results





def convert(filename, data, data_x, type,  generate_mode):
    """转换为生成式数据
    """
    total_results = fold_convert_our_data_ot(data, data_x, type, generate=True, generate_mode=generate_mode)

    with open(filename, 'w') as f:
        for item in total_results:
            f.writelines(json.dumps(item, ensure_ascii=False))
            f.write('\n')



if __name__ == '__main__':

    data = load_data(data_extract_json)
    data_x = np.load(data_extract_npy)
    da_type = "sort"
    match_data_seq2seq_json = '../dataset/our_data/match_data_seq2seq_{}.json'.format(da_type)
    midmatch_data_seq2seq_json = '../dataset/our_data/midmatch_data_seq2seq_{}.json'.format(da_type)
    dismatch_data_seq2seq_json = '../dataset/our_data/dismatch_data_seq2seq_{}.json'.format(da_type)
    convert(match_data_seq2seq_json, data, data_x, type='match', generate_mode=da_type)
    convert(midmatch_data_seq2seq_json, data, data_x, type='midmatch',  generate_mode=da_type)
    convert(dismatch_data_seq2seq_json, data, data_x, type='dismatch',  generate_mode=da_type)


    print(u'输出over！')
