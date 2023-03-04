import os
import random
import torch
import numpy as np

from os.path import join


def _format_arg(arg_name, cutoff=2):
    arg_name = str(arg_name)
    if arg_name is None:
        return arg_name
    
    # Hardcode to handle backslash
    name_splits = arg_name.split('/')
    if len(name_splits) > 1:
        return name_splits[-1]
    # Abbreviate based on underscore
    name_splits = arg_name.split('_')
    if len(name_splits) > 1:
        return ''.join([s[0] for s in name_splits])
    else:
        return arg_name[:cutoff]
        
    
def _seed_everything(seed):
    random.seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def initialize_experiment(args, experiment_name_id='',
                          best_train_metric=1e10, 
                          best_val_metric=1e10):
    
    # Initialize experiments
    _seed_everything(args.seed)
    args.device = (torch.device('cuda:0') 
                   if torch.cuda.is_available() and not args.no_cuda
                   else torch.device('cpu'))
    
    # Experiment name
    args.experiment_name = f'{experiment_name_id}-' if experiment_name_id != '' else ''
    
    dataset_name = args.dataset if args.variant is None else f'{args.dataset}{args.variant}'
    args.experiment_name += f'm={args.model}'  # f'd={dataset_name}-m={args.model}'
    if args.n_shots is None and args.num_examples is not None:
        args.n_shots = args.num_examples
    for arg in ['embedding_config', 'preprocess_config', 'encoder_config', 'decoder_config', 'output_config', 
                'n_blocks', 'n_kernels', 'n_heads', 'embedding_dim', 'kernel_dim', 'kernel_init',
                'lag', 'horizon', 'loss', 'activation', 'dropout', 'layernorm', 'lr', 'optimizer', 'scheduler', 
                'weight_decay', 'batch_size', 'val_metric', 'max_epochs', 'early_stopping_epochs', 'replicate']:
        args.experiment_name += f'-{_format_arg(arg)}={_format_arg(getattr(args, arg), cutoff=None)}'
    args.experiment_name += f'-se={args.seed}'
    args.experiment_name = args.experiment_name.replace('True', '1').replace('False', '0').replace('None', 'na').replace(
        'normal', 'no').replace('xavier', 'xa').replace('identity', 'id').replace('avgpool', 'avgp')
    
    # Checkpointing
    args.best_train_metric = best_train_metric
    args.best_val_metric   = best_val_metric
    
    checkpoint_dir = join(args.checkpoint_dir, args.dataset)
    if not os.path.isdir(checkpoint_dir):
        os.makedirs(checkpoint_dir)
    args.checkpoint_dir = checkpoint_dir
    
    args.best_train_checkpoint_path = join(args.checkpoint_dir, 
                                           f'btrn-{args.experiment_name}.pth')
    args.best_val_checkpoint_path   = join(args.checkpoint_dir, 
                                           f'bval-{args.experiment_name}.pth')
    # Logging
    project_name = f'spacetime-d={dataset_name}-horizon={args.horizon}'
    if args.dataset_type == 'grokking':
        for arg in ['vocab_size', 'num_examples', 'input_seq_len']:
            project_name += f'-{_format_arg(arg)}={_format_arg(getattr(args, arg), cutoff=None)}'
            args.experiment_name += f'-{_format_arg(arg)}={_format_arg(getattr(args, arg), cutoff=None)}'
    
    if not args.no_wandb:
        import wandb
        run_name = args.experiment_name
        wandb.init(config={},
                   entity=args.wandb_entity,
                   name=run_name,
                   project=project_name,
                   dir=args.log_dir)
        wandb.config.update(args)
    else:
        wandb = None
        
    # Local logging
    args.log_dir = join(args.log_dir, project_name)
    if not os.path.exists(args.log_dir):
        os.makedirs(args.log_dir)
        print(f'-> Created logging directory at {args.log_dir}!')
    log_id = args.experiment_name
    args.log_results_path = join(args.log_dir, f'r-{log_id}.csv')
    args.log_configs_path = join(args.log_dir, f'c-{log_id}.csv')
    args.log_results_dict = {'epoch': [], 'split': []}
    
    return wandb