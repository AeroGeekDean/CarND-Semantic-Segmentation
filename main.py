#!/usr/bin/env python3
import os.path
import tensorflow as tf
import helper
import warnings
from distutils.version import LooseVersion
import project_tests as tests
import time


# Check TensorFlow Version
assert LooseVersion(tf.__version__) >= LooseVersion('1.0'), 'Please use TensorFlow version 1.0 or newer.  You are using {}'.format(tf.__version__)
print('TensorFlow Version: {}'.format(tf.__version__))

# Check for a GPU
if not tf.test.gpu_device_name():
    warnings.warn('No GPU found. Please use a GPU to train your neural network.')
else:
    print('Default GPU Device: {}'.format(tf.test.gpu_device_name()))


def load_vgg(sess, vgg_path):
    """
    Load Pretrained VGG Model into TensorFlow.
    :param sess: TensorFlow Session
    :param vgg_path: Path to vgg folder, containing "variables/" and "saved_model.pb"
    :return: Tuple of Tensors from VGG model (image_input, keep_prob, layer3_out, layer4_out, layer7_out)
    """
    vgg_tag = 'vgg16'
    vgg_input_tensor_name = 'image_input:0' # imgage_input
    vgg_keep_prob_tensor_name = 'keep_prob:0' # keep_prob
    vgg_layer3_out_tensor_name = 'layer3_out:0' # layer3_out
    vgg_layer4_out_tensor_name = 'layer4_out:0' # layer4_out
    vgg_layer7_out_tensor_name = 'layer7_out:0' # layer7_out

    tf.saved_model.loader.load(sess, [vgg_tag], vgg_path)
    graph = tf.get_default_graph()

    imgage_input = graph.get_tensor_by_name(vgg_input_tensor_name)
    keep_prob    = graph.get_tensor_by_name(vgg_keep_prob_tensor_name)
    layer3_out   = graph.get_tensor_by_name(vgg_layer3_out_tensor_name)
    layer4_out   = graph.get_tensor_by_name(vgg_layer4_out_tensor_name)
    layer7_out   = graph.get_tensor_by_name(vgg_layer7_out_tensor_name)

    return (imgage_input, keep_prob, layer3_out, layer4_out, layer7_out)
tests.test_load_vgg(load_vgg, tf)


def layers(vgg_layer3_out, vgg_layer4_out, vgg_layer7_out, num_classes):
    """
    Create the layers for a fully convolutional network.  Build skip-layers using the vgg layers.
    :param vgg_layer3_out: TF Tensor for VGG Layer 3 output
    :param vgg_layer4_out: TF Tensor for VGG Layer 4 output
    :param vgg_layer7_out: TF Tensor for VGG Layer 7 output
    :param num_classes: Number of classes to classify
    :return: The Tensor for the last layer of output
    """
    # TODO: Implement function

    # print('vgg_layer7_out.shape={}'.format(vgg_layer7_out.shape))

    # reduce num filters from 4096 to 'num_classes'
    conv_1x1_out = tf.layers.conv2d(vgg_layer7_out, num_classes,
                                    kernel_size=1,
                                    strides=1,
                                    padding='same',
                                    kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-3))

    # print('conv_1x1_out.shape={}'.format(conv_1x1_out.shape))

    out = tf.layers.conv2d_transpose(conv_1x1_out, num_classes,
                                     kernel_size=4,
                                     strides=2,
                                     padding='same',
                                     kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-3))

    # print('upsample1_out.shape={}'.format(out.shape))

    vgg_layer4_out1 = tf.layers.conv2d(vgg_layer4_out, num_classes,
                                       kernel_size=1,
                                       strides=1,
                                       padding='same',
                                       kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-3))

    out = tf.add(out, vgg_layer4_out1)

    out = tf.layers.conv2d_transpose(out, num_classes,
                                     kernel_size=4,
                                     strides=2,
                                     padding='same',
                                     kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-3))

    # print('upsample2_out.shape={}'.format(out.shape))

    vgg_layer3_out1 = tf.layers.conv2d(vgg_layer3_out, num_classes,
                                       kernel_size=1,
                                       strides=1,
                                       padding='same',
                                       kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-3))
    out = tf.add(out, vgg_layer3_out1)

    out = tf.layers.conv2d_transpose(out, num_classes,
                                     kernel_size=16,
                                     strides=8,
                                     padding='same',
                                     kernel_regularizer=tf.contrib.layers.l2_regularizer(1e-3))

    # print('upsample3_out.shape={}'.format(out.shape))

    return out

tests.test_layers(layers)


def optimize(nn_last_layer, correct_label, learning_rate, num_classes):
    """
    Build the TensorFLow loss and optimizer operations.
    :param nn_last_layer: TF Tensor of the last layer in the neural network
    :param correct_label: TF Placeholder for the correct label image
    :param learning_rate: TF Placeholder for the learning rate
    :param num_classes: Number of classes to classify
    :return: Tuple of (logits, train_op, cross_entropy_loss)
    """
    # TODO: Implement function
    logits = tf.reshape(nn_last_layer, (-1, num_classes))
    y = tf.reshape(correct_label, (-1, num_classes))

    cross_entropy_loss = tf.reduce_mean(
        tf.nn.softmax_cross_entropy_with_logits(logits=logits, labels=y))

    non_vgg_vars = [x for x in tf.trainable_variables() if 'VGG16' not in x.name]

    train_op = tf.train.AdamOptimizer(learning_rate).minimize(
        cross_entropy_loss,
        var_list=non_vgg_vars)

    L2_loss = 0 # TODO: Need to look up how to implement this....!

    return (logits, train_op, (cross_entropy_loss + L2_loss))

tests.test_optimize(optimize)


def train_nn(sess, epochs, batch_size, get_batches_fn, train_op, cross_entropy_loss, input_image,
             correct_label, keep_prob, learning_rate):
    """
    Train neural network and print out the loss during training.
    :param sess: TF Session
    :param epochs: Number of epochs
    :param batch_size: Batch size
    :param get_batches_fn: Function to get batches of training data.  Call using get_batches_fn(batch_size)
    :param train_op: TF Operation to train the neural network
    :param cross_entropy_loss: TF Tensor for the amount of loss
    :param input_image: TF Placeholder for input images
    :param correct_label: TF Placeholder for label images
    :param keep_prob: TF Placeholder for dropout keep probability
    :param learning_rate: TF Placeholder for learning rate
    """
    # TODO: Implement function
    
    totalstarttime = time.clock()
    
    sess.run(tf.global_variables_initializer())

    for i in range(epochs):
        training_loss = 0
        training_samples = 0
        print('running epochs:', i)
        
        starttime = time.clock()
        
        for image, label in get_batches_fn(batch_size):
            training_samples += len(image)
            
            loss,_ = sess.run([cross_entropy_loss, train_op],
                              feed_dict={input_image: image,
                                         correct_label: label,
                                         keep_prob: 0.8})
            training_loss += loss

        # calc training loss
        training_loss /= training_samples
        endtime = time.clock()
        training_time = endtime - starttime
        print('epoch {} execution took {} sec,'.format(i, training_time) +
              ' with training loss: {}'.format(training_loss))

    totalendtime = time.clock()
    totaltime = totalendtime - totalstarttime
    print('total execution took {} seconds'.format(totaltime))
            
tests.test_train_nn(train_nn)


def run():
    num_classes = 2
    image_shape = (160, 576)
#     data_dir = './data'
    data_dir = '/data'
    runs_dir = './runs'
    
    print('testing for kitti dataset')
    tests.test_for_kitti_dataset(data_dir)

    # Download pretrained vgg model
    print('maybe download pretrained vgg')
    helper.maybe_download_pretrained_vgg(data_dir)

    # OPTIONAL: Train and Inference on the cityscapes dataset instead of the Kitti dataset.
    # You'll need a GPU with at least 10 teraFLOPS to train on.
    #  https://www.cityscapes-dataset.com/

    print('init run params')
    epochs = 25
    batch_size = 1
    learning_rate = tf.constant(0.0001)

    with tf.Session() as sess:
        # Path to vgg model
        vgg_path = os.path.join(data_dir, 'vgg')
        # Create function to get batches
        get_batches_fn = helper.gen_batch_function(os.path.join(data_dir, 'data_road/training'), image_shape)

        # OPTIONAL: Augment Images for better results
        #  https://datascience.stackexchange.com/questions/5224/how-to-prepare-augment-images-for-neural-network

        # TODO: Build NN using load_vgg, layers, and optimize function
        shape = [None, image_shape[0], image_shape[1], 3]
        correct_label = tf.placeholder(tf.float32, [None, image_shape[0], image_shape[1], num_classes])

        print('load_vgg()...')
        input_image, keep_prob, layer3_out, layer4_out, layer7_out = load_vgg(sess, vgg_path)

        print('layers()...')
        final_output = layers(layer3_out, layer4_out, layer7_out, num_classes)

        print('optimize()...')
        logits, train_op, loss = optimize(final_output, correct_label, learning_rate, num_classes)

        # TODO: Train NN using the train_nn function
        train_nn(sess, epochs, batch_size, get_batches_fn, train_op, loss,
                 input_image, correct_label, keep_prob, learning_rate)

        # TODO: Save inference data using helper.save_inference_samples
        print('Saving inference samples')
        helper.save_inference_samples(runs_dir, data_dir, sess, image_shape, logits, keep_prob, input_image)

        # OPTIONAL: Apply the trained model to a video


if __name__ == '__main__':
    run()
